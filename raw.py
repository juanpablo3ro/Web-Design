import sqlite3
import json
import re
import os
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
import csv
from io import StringIO
from flask import make_response
from flask_mail import Mail, Message  # Importar Flask-Mail
from ai_drivers import analizar_drivers, check_ollama_status


app = Flask(__name__)
DATABASE = 'inscripciones.db' # Corrected database name

# Configuración de Flask-Mail para Gmail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'proditeamweb@gmail.com'
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'tu_contraseña_de_aplicación')  # Usar variable de entorno
app.config['MAIL_DEFAULT_SENDER'] = 'proditeamweb@gmail.com'

mail = Mail(app)  # Inicializar extensión Mail

# Define get_db primero para que init_db pueda usarla
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # This allows accessing columns by name
    return conn

# Función para enviar email de notificación
def enviar_email_notificacion(datos_participante):
    try:
        subject = "Nuevo participante registrado en PRODI"
        recipient = "proditeamweb@gmail.com"  # Puedes cambiar a tu dirección personal
        
        # Crear un mensaje con formato HTML para mejor presentación
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center;">
                <img src="https://proditeam.com/wp-content/uploads/2023/05/logo-PRODI-2023-2.png" alt="Logo PRODI" style="max-width: 150px; margin-bottom: 20px;">
            </div>
            <h2 style="color: #008c8c; border-bottom: 2px solid #008c8c; padding-bottom: 10px;">Nuevo Participante Registrado</h2>
            <p><strong>Nombre:</strong> {datos_participante.get('nombres_apellidos')}</p>
            <p><strong>Correo:</strong> {datos_participante.get('correo_electronico')}</p>
            <p><strong>Teléfono:</strong> {datos_participante.get('telefono')}</p>
            <p><strong>País:</strong> {datos_participante.get('pais')}</p>
            <p><strong>Edad:</strong> {datos_participante.get('edad')}</p>
            <p><strong>Sexo:</strong> {datos_participante.get('sexo')}</p>
            <p><strong>Fecha de Registro:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <div style="margin-top: 30px; padding: 15px; background-color: #f5f5f5; border-radius: 5px;">
                <p style="margin: 0;">Para ver los detalles completos, ingresa al <a href="https://proditeam.com/gestion_participantes" style="color: #008c8c; text-decoration: none; font-weight: bold;">Panel de Administración</a></p>
            </div>
            <div style="margin-top: 30px; font-size: 12px; color: #777; text-align: center;">
                <p>Este es un mensaje automático, por favor no responda a este correo.</p>
            </div>
        </div>
        """
        
        msg = Message(
            subject=subject,
            recipients=[recipient],
            html=html_content
        )
        
        mail.send(msg)
        print(f"Email de notificación enviado a {recipient}")
        return True
    except Exception as e:
        print(f"Error al enviar email: {e}")
        return False

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        # Create inscripciones table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inscripciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_inscripcion TEXT DEFAULT CURRENT_TIMESTAMP,
                nombres_apellidos TEXT NOT NULL,
                correo_electronico TEXT,
                telefono TEXT,
                pais TEXT,
                edad INTEGER,
                sexo TEXT,
                referido_por TEXT,
                whatsapp_prodi TEXT,
                diabetes TEXT,
                hipertension TEXT,
                infartos_acv TEXT,
                inicio TEXT,
                activo TEXT DEFAULT 'Sí',
                renuncio TEXT DEFAULT 'No',
                termino TEXT DEFAULT 'No',
                sesion_numero INTEGER DEFAULT 1,
                atiende_reuniones TEXT,
                desea_bajar_peso TEXT,
                porcentaje_bajar REAL,
                tiempo_bajar TEXT,
                peso_actual REAL,
                talla_cm REAL,
                notas TEXT,
                motivo_union TEXT,
                objetivos_lograr TEXT,
                inquietudes_desafios TEXT,
                sentimiento_trabajo_grupo TEXT,
                programa_mas_gratificante TEXT,
                fecha_hoy TEXT,
                peso_hoy REAL,
                imc_registro REAL,
                analisis_driver TEXT
            )
        ''')
        
        # Verificar columnas existentes
        cursor.execute("PRAGMA table_info(inscripciones)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Verificar si la columna imc_registro existe, y si no, añadirla
        if 'imc_registro' not in columns:
            cursor.execute("ALTER TABLE inscripciones ADD COLUMN imc_registro REAL")
        
        # Verificar si la columna renuncio existe, y si no, añadirla
        if 'renuncio' not in columns:
            cursor.execute("ALTER TABLE inscripciones ADD COLUMN renuncio TEXT DEFAULT 'No'")
            
        # Verificar si la columna termino existe, y si no, añadirla
        if 'termino' not in columns:
            cursor.execute("ALTER TABLE inscripciones ADD COLUMN termino TEXT DEFAULT 'No'")
            
        # Verificar si la columna analisis_driver existe, y si no, añadirla
        if 'analisis_driver' not in columns:
            cursor.execute("ALTER TABLE inscripciones ADD COLUMN analisis_driver TEXT")
        
        # Create historial_pesos table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historial_pesos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inscripcion_id INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                peso REAL NOT NULL,
                imc REAL,
                FOREIGN KEY (inscripcion_id) REFERENCES inscripciones (id)
            )
        ''')
        db.commit()
        db.close()

# Ensure the database and tables are created when the application starts
with app.app_context():
    init_db()

def clean_phone_number(phone_number):
    if not phone_number:
        return None
    # Remove non-digit characters
    cleaned = re.sub(r'\D', '', phone_number)
    # If the original number started with '+', keep it
    if phone_number.strip().startswith('+'):
        cleaned = '+' + cleaned
    # Add default country code if not present (assuming Spain for +34)
    if not cleaned.startswith('+'):
        cleaned = '+34' + cleaned
    return cleaned

# Función para analizar drivers con Ollama
def analizar_drivers(respuestas):
    try:
        # Formatear las respuestas para el prompt en el formato que esperaría CoachPRODI
        prompt = """
        Por favor analiza las siguientes respuestas de un participante del programa PRODI según el marco de impulsores del comportamiento humano:

        1. ¿Qué te motivó a unirte a este programa? 
        {motivacion}
        
        2. ¿Qué esperas lograr al participar? 
        {logros}
        
        3. ¿Qué inquietudes o desafíos tienes sobre los cambios en tu estilo de vida?
        {desafios}
        
        4. ¿Cómo te sientes al trabajar con otras personas?
        {trabajo_grupo}
        
        5. ¿Qué haría que este programa fuera más gratificante o significativo para ti?
        {gratificante}
        
        Basado en el marco de impulsores del comportamiento humano (Supervivencia/Seguridad, Poder/Influencia, Pertenencia/Conexión, Estima/Reconocimiento, Propósito/Significado, Placer/Recompensa, Curiosidad/Aprendizaje, Miedo/Evitación), identifica el impulsor principal y proporciona tu análisis completo.
        """.format(
            motivacion=respuestas.get('motivo_union', 'No proporcionado'),
            logros=respuestas.get('objetivos_lograr', 'No proporcionado'),
            desafios=respuestas.get('inquietudes_desafios', 'No proporcionado'),
            trabajo_grupo=respuestas.get('sentimiento_trabajo_grupo', 'No proporcionado'),
            gratificante=respuestas.get('programa_mas_gratificante', 'No proporcionado')
        )
        
        # Realizar la llamada al modelo CoachPRODI a través de la API de Ollama
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'CoachPRODI',  # Usar específicamente el modelo CoachPRODI
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.7,  
                    'top_p': 0.9,
                    'max_tokens': 2000   # Permitir respuestas más largas para análisis detallados
                }
            },
            timeout=120  # Timeout más largo para análisis más profundos
        )
        
        if response.status_code == 200:
            result = response.json()
            analysis = result.get('response', '')
            
            # Formatear la respuesta para presentación en la UI
            formatted_analysis = analysis.strip()
            
            # Asegurarnos de que la respuesta comience con una identificación clara del driver principal
            if not any(driver in formatted_analysis[:150].lower() for driver in ["supervivencia", "poder", "pertenencia", "estima", "propósito", "placer", "curiosidad", "miedo"]):
                formatted_analysis = "Análisis de Driver:\n\n" + formatted_analysis
                
            return formatted_analysis
        else:
            error_msg = f"Error al comunicarse con Ollama (Código: {response.status_code})"
            print(error_msg)
            print(f"Respuesta: {response.text}")
            return error_msg
    except requests.exceptions.Timeout:
        return "El análisis está tomando más tiempo del esperado. Por favor, intente nuevamente."
    except Exception as e:
        error_msg = f"Error al analizar drivers: {str(e)}"
        print(error_msg)
        return error_msg

# Función para verificar si Ollama está disponible y el modelo está cargado
def check_ollama_model(model_name='CoachPRODI'):
    try:
        # Primero verificamos si el servicio Ollama está funcionando
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        
        if response.status_code != 200:
            return False, f"El servicio Ollama no está respondiendo (Código: {response.status_code})"
        
        # Verificamos si el modelo solicitado está disponible
        models_data = response.json()
        available_models = []
        
        # Extraer nombres de modelos dependiendo de la estructura de la respuesta
        if 'models' in models_data:
            available_models = [model['name'] for model in models_data['models']]
        else:
            # Adaptarse a diferentes formatos de respuesta
            for tag_data in models_data.values():
                if isinstance(tag_data, list):
                    available_models.extend([model['name'] for model in tag_data])
        
        if model_name in available_models:
            return True, f"Modelo {model_name} disponible"
        else:
            return False, f"Modelo {model_name} no encontrado. Modelos disponibles: {', '.join(available_models)}"
    
    except requests.exceptions.ConnectionError:
        return False, "No se pudo conectar con Ollama. Asegúrate de que el servicio esté en ejecución."
    except requests.exceptions.Timeout:
        return False, "La conexión con Ollama ha agotado el tiempo de espera."
    except Exception as e:
        return False, f"Error al verificar Ollama: {str(e)}"

# Ruta para verificar el estado de Ollama desde la interfaz
@app.route('/api/check-ollama-status')
def api_check_ollama_status():
    status = check_ollama_status()
    return jsonify(status)

@app.route('/api/analizar-drivers/<int:id>', methods=['POST'])
def analizar_drivers_endpoint(id):
    try:
        # Verificar el estado de Ollama primero
        ollama_status = check_ollama_status()
        if not ollama_status['success']:
            return jsonify({'error': f"No se puede realizar el análisis: {ollama_status['message']}"}), 503
        
        # Obtener datos del participante
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM inscripciones WHERE id = ?', (id,))
        participante = cursor.fetchone()
        
        if not participante:
            db.close()
            return jsonify({'error': 'Participante no encontrado'}), 404
        
        # Crear diccionario con las respuestas
        respuestas = {
            'motivo_union': participante['motivo_union'] or '',
            'objetivos_lograr': participante['objetivos_lograr'] or '',
            'inquietudes_desafios': participante['inquietudes_desafios'] or '',
            'sentimiento_trabajo_grupo': participante['sentimiento_trabajo_grupo'] or '',
            'programa_mas_gratificante': participante['programa_mas_gratificante'] or ''
        }
        
        # Verificar si hay suficiente información
        responses_filled = [r for r in respuestas.values() if r.strip()]
        if len(responses_filled) < 2:
            db.close()
            return jsonify({'error': 'No hay suficiente información para analizar los drivers. Se necesitan al menos dos respuestas.'}), 400
        
        # Realizar el análisis
        analisis = analizar_drivers(respuestas)
        
        # Guardar en la base de datos
        cursor.execute('UPDATE inscripciones SET analisis_driver = ? WHERE id = ?', (analisis, id))
        db.commit()
        
        db.close()
        return jsonify({
            'success': True,
            'analisis': analisis
        })
    except Exception as e:
        if 'db' in locals() and db:
            db.rollback()
            db.close()
        print(f"Error al analizar drivers: {e}")
        return jsonify({'error': str(e)}), 500

# --- Rutas de Páginas ---
@app.route('/api/analizar-drivers/evaluate', methods=['POST'])
def evaluate_drivers():
    try:
        data = request.json
        
        # Verificar que todos los campos requeridos estén presentes
        required_fields = ['motivo_union', 'objetivos_lograr', 'inquietudes_desafios', 'sentimiento_trabajo_grupo', 'programa_mas_gratificante']
        
        # Comprobar si faltan campos
        for field in required_fields:
            if field not in data or not data[field].strip():
                return jsonify({'error': f'Falta el campo requerido: {field}'}), 400

        # Realizar el análisis usando el módulo de IA
        analysis = analizar_drivers(data)

        return jsonify({'success': True, 'analisis': analysis}), 200

    except Exception as e:
        print(f"Error en evaluación de drivers: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/evaluar_ai')
def evaluar_ai():
    return render_template('evaluate_ai.html')

@app.route('/')
def home(): # Nombre de la función para 'Home'
    db = get_db()
    cursor = db.cursor()
    # Select id and nombres_apellidos for the dropdown
    cursor.execute("SELECT id, nombres_apellidos FROM inscripciones ORDER BY nombres_apellidos")
    inscripciones_nombres = cursor.fetchall()
    db.close()
    return render_template('index.html', inscripciones_nombres=inscripciones_nombres)

@app.route('/nueva_inscripcion') # Ruta para 'Nueva Inscripción'
def nueva_inscripcion(): # Nombre de la función para 'Nueva Inscripción'
    return render_template('formulario.html')

@app.route('/inscripciones', methods=['POST'])
def save_inscripcion():
    try:
        data = request.form
        db = get_db()
        cursor = db.cursor()

        telefono_cleaned = clean_phone_number(data.get('telefono'))

        # Calculate initial IMC if peso_actual and talla_cm are provided
        peso_actual_val = float(data.get('peso_actual')) if data.get('peso_actual') else None
        talla_cm_val = float(data.get('talla_cm')) if data.get('talla_cm') else None
        imc_registro_val = None
        if peso_actual_val and talla_cm_val:
            imc_registro_val = round(peso_actual_val / ((talla_cm_val / 100) ** 2), 2)

        # Get current date for fecha_hoy and peso_hoy if not provided
        current_date = datetime.now().strftime('%Y-%m-%d')
        fecha_hoy_val = data.get('fecha_hoy') or current_date
        peso_hoy_val = float(data.get('peso_hoy')) if data.get('peso_hoy') else peso_actual_val

        cursor.execute('''
            INSERT INTO inscripciones (
                nombres_apellidos, correo_electronico, telefono, pais, edad, sexo,
                referido_por, whatsapp_prodi, diabetes, hipertension, infartos_acv,
                inicio, activo, sesion_numero, atiende_reuniones, desea_bajar_peso,
                porcentaje_bajar, tiempo_bajar, peso_actual, talla_cm, notas,
                motivo_union, objetivos_lograr, inquietudes_desafios,
                sentimiento_trabajo_grupo, programa_mas_gratificante, fecha_hoy, peso_hoy, imc_registro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('nombres_apellidos'), data.get('correo_electronico'), telefono_cleaned,
            data.get('pais'), data.get('edad'), data.get('sexo'),
            data.get('referido_por'), data.get('whatsapp_prodi'), data.get('diabetes'),
            data.get('hipertension'), data.get('infartos_acv'), data.get('inicio'),
            data.get('activo', 'Sí'), data.get('sesion_numero', 1), data.get('atiende_reuniones'),
            data.get('desea_bajar_peso'), data.get('porcentaje_bajar'), data.get('tiempo_bajar'),
            peso_actual_val, talla_cm_val, data.get('notas'),
            data.get('motivo_union'), data.get('objetivos_lograr'), data.get('inquietudes_desafios'),
            data.get('sentimiento_trabajo_grupo'), data.get('programa_mas_gratificante'),
            fecha_hoy_val, peso_hoy_val, imc_registro_val # Added imc_registro here
        ))
        inscripcion_id = cursor.lastrowid

        # Insert initial weight into historial_pesos if provided
        if peso_actual_val and talla_cm_val:
            cursor.execute('''
                INSERT INTO historial_pesos (inscripcion_id, fecha, peso, imc)
                VALUES (?, ?, ?, ?)
            ''', (inscripcion_id, current_date, peso_actual_val, imc_registro_val))

        db.commit()
        
        # Enviar email de notificación después de guardar en la base de datos
        enviar_email_notificacion(data)
        
        db.close()
        return redirect(url_for('mensaje_gracias')) # Redirige a la función de mensaje de gracias
    except Exception as e:
        # It's good practice to rollback on error to keep the DB consistent
        if 'db' in locals() and db:
            db.rollback()
        print(f"Error al guardar inscripción: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        # Ensure db connection is closed even if an error occurs
        if 'db' in locals() and db:
            db.close()

@app.route('/mensaje_gracias') # Ruta para 'Mensaje de Gracias'
def mensaje_gracias(): # Nombre de la función para 'Mensaje de Gracias'
    return render_template('thank_you_message.html')

@app.route('/ver_inscripciones')
def ver_inscripciones():
    db = get_db()
    cursor = db.cursor()
    # Fetch all data for the detailed table
    cursor.execute("SELECT * FROM inscripciones ORDER BY nombres_apellidos")
    inscripciones = cursor.fetchall()
    db.close()
    return render_template('ver_inscripciones.html', inscripciones=inscripciones)

@app.route('/gestion_participantes')
def gestion_participantes():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, nombres_apellidos FROM inscripciones ORDER BY nombres_apellidos")
    inscripciones_nombres = cursor.fetchall()
    
    return render_template('participante.html', inscripciones_nombres=inscripciones_nombres)

@app.route('/api/inscripcion/<int:inscripcion_id>')
def get_inscripcion_data(inscripcion_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM inscripciones WHERE id = ?', (inscripcion_id,))
    inscripcion_data = cursor.fetchone()

    if inscripcion_data:  # Condición corregida
        # Fetch historical weights
        cursor.execute('SELECT fecha, peso, imc FROM historial_pesos WHERE inscripcion_id = ? ORDER BY fecha ASC', (inscripcion_id,))
        historial_pesos = cursor.fetchall()
        
        data = dict(inscripcion_data)
        data['historial_pesos'] = [dict(row) for row in historial_pesos]
        
        # Calculate IMC at registration if not already stored or if needed for display
        peso_actual_for_imc = data.get('peso_actual')
        talla_cm_for_imc = data.get('talla_cm')
        if peso_actual_for_imc and talla_cm_for_imc:
            data['imc_registro'] = round(float(peso_actual_for_imc) / ((float(talla_cm_for_imc) / 100) ** 2), 2)
        else:
            data['imc_registro'] = None

        # Calculate current IMC based on peso_hoy
        peso_hoy_val = data.get('peso_hoy')
        if peso_hoy_val and talla_cm_for_imc:
            data['imc_hoy'] = round(float(peso_hoy_val) / ((float(talla_cm_for_imc) / 100) ** 2), 2)
        else:
            data['imc_hoy'] = None

        # Calculate weight change
        if data.get('peso_actual') is not None and data.get('peso_hoy') is not None:
            data['cambio_de_peso'] = round(data['peso_hoy'] - data['peso_actual'], 2)
        else:
            data['cambio_de_peso'] = None

        db.close()
        return jsonify(data), 200

    db.close()
    return jsonify({'error': 'Participante no encontrado'}), 404

@app.route('/api/inscripcion/<int:inscripcion_id>/update', methods=['POST'])
def update_inscripcion_data(inscripcion_id):
    try:
        data = request.json
        db = get_db()
        cursor = db.cursor()

        update_fields = []
        update_values = []
        
        updatable_fields = [
            'nombres_apellidos', 'correo_electronico', 'telefono', 'pais', 'edad', 'sexo',
            'referido_por', 'whatsapp_prodi', 'diabetes', 'hipertension', 'infartos_acv',
            'inicio', 'activo', 'renuncio', 'termino', 'sesion_numero', 'atiende_reuniones', 'desea_bajar_peso',
            'porcentaje_bajar', 'tiempo_bajar', 'notas', 'motivo_union', 'objetivos_lograr',
            'inquietudes_desafios', 'sentimiento_trabajo_grupo', 'programa_mas_gratificante',
            'peso_actual', 'talla_cm', 'analisis_driver' # Añadido analisis_driver
        ]

        for field in updatable_fields:
            if field in data:  # Condición corregida
                if field == 'telefono':
                    update_values.append(clean_phone_number(data[field]))
                else:
                    update_values.append(data[field])
                update_fields.append(f"{field} = ?")
                
        if not update_fields and 'peso_hoy' not in data and 'fecha_hoy' not in data:  # Condición corregida
            return jsonify({'error': 'No hay campos para actualizar.'}), 400

        # Update main inscripciones table first
        if update_fields:
            update_query = f"UPDATE inscripciones SET {', '.join(update_fields)} WHERE id = ?"
            update_values.append(inscripcion_id)
            cursor.execute(update_query, tuple(update_values))

        # Handle peso_hoy and fecha_hoy separately, as they also involve historial_pesos
        if 'peso_hoy' in data and 'fecha_hoy' in data:  # Condición corregida
            fecha_hoy = data['fecha_hoy']
            peso_hoy = float(data['peso_hoy']) if data['peso_hoy'] else None

            # Get talla_cm to calculate IMC for the new weight entry
            cursor.execute('SELECT talla_cm FROM inscripciones WHERE id = ?', (inscripcion_id,))
            result = cursor.fetchone()
            talla_cm = result['talla_cm'] if result else None

            if peso_hoy is not None and fecha_hoy and talla_cm is not None:
                imc_hoy = round(peso_hoy / ((talla_cm / 100) ** 2), 2)
                
                # Check if a weight entry for this date already exists
                cursor.execute('SELECT id FROM historial_pesos WHERE inscripcion_id = ? AND fecha = ?', (inscripcion_id, fecha_hoy))
                existing_entry = cursor.fetchone()

                if existing_entry:
                    # Update existing weight entry
                    cursor.execute('''
                        UPDATE historial_pesos
                        SET peso = ?, imc = ?
                        WHERE id = ?
                    ''', (peso_hoy, imc_hoy, existing_entry['id']))
                else:
                    # Insert new weight entry
                    cursor.execute('''
                        INSERT INTO historial_pesos (inscripcion_id, fecha, peso, imc)
                        VALUES (?, ?, ?, ?)
                    ''', (inscripcion_id, fecha_hoy, peso_hoy, imc_hoy))
                
                # Update fecha_hoy and peso_hoy in the main inscripciones table
                cursor.execute('''
                    UPDATE inscripciones
                    SET fecha_hoy = ?, peso_hoy = ?
                    WHERE id = ?
                ''', (fecha_hoy, peso_hoy, inscripcion_id))

        db.commit()
        db.close()
        return jsonify({'message': 'Datos actualizados con éxito!'}), 200
    except Exception as e:
        if 'db' in locals() and db:
            db.rollback()
        print(f"Error al actualizar datos: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'db' in locals() and db:
            db.close()


@app.route('/enviar_mensajes_whatsapp') # Ruta para 'Enviar Mensajes'
def enviar_mensajes_whatsapp(): # Nombre de la función para 'Enviar Mensajes'
    return render_template('whatsapp_contacts.html')

@app.route('/api/participants_by_session/<int:session_number>')
def get_participants_by_session(session_number):
    db = get_db()
    cursor = db.cursor()
    
    # Si la solicitud es para Completados (sesión 17)
    if session_number == 17:
        cursor.execute('''
            SELECT id, nombres_apellidos, telefono, sesion_numero, inicio, activo, renuncio, termino
            FROM inscripciones
            WHERE sesion_numero = 17 OR termino = 'Si'
            ORDER BY nombres_apellidos
        ''')
        
        # Actualizar cualquier participante que tenga termino = 'Si' pero sesion_numero != 17
        cursor.execute('''
            UPDATE inscripciones
            SET sesion_numero = 17
            WHERE termino = 'Si' AND sesion_numero != 17
        ''')
        db.commit()
    else:
        # Para las sesiones regulares, excluir los completados
        cursor.execute('''
            SELECT id, nombres_apellidos, telefono, sesion_numero, inicio, activo, renuncio, termino
            FROM inscripciones
            WHERE sesion_numero = ? AND sesion_numero != 17
            ORDER BY nombres_apellidos
        ''', (session_number,))
    
    participants = cursor.fetchall()
    db.close()
    
    participants_list = [dict(row) for row in participants]
    
    # Resto del código para WhatsApp links...
    
      
    # Diccionario de enlaces de YouTube para cada sesión
    youtube_links = {
        1: "https://www.youtube.com/watch?v=zuZ-WtQnTdw",
        2: "https://www.youtube.com/watch?v=ZUmhz0GeVvQ",
        3: "https://www.youtube.com/watch?v=psNzJX3wya0&t=74s",
        4: "https://www.youtube.com/watch?v=5siGiDbz9GI&t=1s",
        5: "https://www.youtube.com/watch?v=CZCxzUHtDmU&t=338s",
        6: "https://www.youtube.com/watch?v=kFqfLQCMsdA&t=22s",
        7: "https://www.youtube.com/watch?v=qXYAvEyX7LQ&t=38s",
        8: "https://www.youtube.com/watch?v=c5Bw65AhdzA&t=15s",
        9: "https://www.youtube.com/watch?v=8XURedprycc&t=17s",
        10: "https://www.youtube.com/watch?v=WXuFC9o1xGU&t=18s",
        11: "https://www.youtube.com/watch?v=CbKMo_2upr8&t=20s",
        12: "https://www.youtube.com/watch?v=iLDI-JP7KM8&t=30s",
        13: "https://www.youtube.com/watch?v=xcPheBx0MXE&t=21s",
        14: "https://www.youtube.com/watch?v=uTFVh1CmGRU&t=21s",
        15: "https://www.youtube.com/watch?v=eg76uv2kVMg&t=49s",
        16: "https://www.youtube.com/watch?v=FsaJA2C2RK4&t=95s"
    }
    
    # Nuevo template del mensaje con URL del programa al final
    message_text_template = "Hola [NOMBRE_PARTICIPANTE], te comparto el contenido de la Sesión [NUMERO_SESION] de esta semana: [YOUTUBE_LINK]. Recuerda que toda la información y herramientas del programa las pueden encontrar en https://proditeam.com/programa-prodi/."
    
    for p in participants_list:
        cleaned_whatsapp_number = clean_phone_number(p['telefono'])
        
        if cleaned_whatsapp_number:
            session_num = p['sesion_numero']
            # Obtener el enlace de YouTube correspondiente a la sesión
            youtube_link = youtube_links.get(session_num, "https://proditeam.com/programa-prodi/")
            
            # Personalizar el mensaje
            personal_message_text = message_text_template.replace("[NOMBRE_PARTICIPANTE]", p['nombres_apellidos'].split(' ')[0])
            personal_message_text = personal_message_text.replace("[NUMERO_SESION]", str(session_num))
            personal_message_text = personal_message_text.replace("[YOUTUBE_LINK]", youtube_link)
            
            # URL-encode the message for WhatsApp link
            import urllib.parse
            encoded_message = urllib.parse.quote_plus(personal_message_text)
            
            p['whatsapp_link'] = f"https://wa.me/{cleaned_whatsapp_number}?text={encoded_message}"
        else:
            p['whatsapp_link'] = '#' # No WhatsApp link if no phone number
            
    return jsonify(participants_list), 200

@app.route('/dashboard')
def dashboard():
    db = get_db()
    cursor = db.cursor()
    
    # Estadísticas 1: Cuántos inician el programa
    cursor.execute('''
        SELECT inicio, COUNT(*) as recuento 
        FROM inscripciones 
        WHERE inicio IS NOT NULL
        GROUP BY inicio
        ORDER BY inicio DESC
    ''')
    inicio_stats = cursor.fetchall()
    
# Calcular totales para "Inicio"
    total_inicio = sum(stat['recuento'] for stat in inicio_stats)
    inicio_data = {
        'labels': [stat['inicio'] for stat in inicio_stats],
        'data': [stat['recuento'] for stat in inicio_stats],
        'percentages': [round((stat['recuento'] / total_inicio) * 100, 1) if total_inicio > 0 else 0 
                        for stat in inicio_stats]
    }
    
    # Estadísticas 2: Datos generales de quienes inician (Si)
    cursor.execute('''
        SELECT COUNT(*) as recuento, 
               ROUND(AVG(edad), 1) as promedio_edad,
               MIN(edad) as min_edad, 
               MAX(edad) as max_edad,
               ROUND(AVG(peso_actual), 1) as peso_basal
        FROM inscripciones 
        WHERE inicio = 'Si'
    ''')
    general_stats = cursor.fetchone()
    
    # Estadísticas 3: Distribución por sexo entre quienes inician
    cursor.execute('''
        SELECT sexo, COUNT(*) as recuento 
        FROM inscripciones 
        WHERE inicio = 'Si' AND sexo IS NOT NULL
        GROUP BY sexo
        ORDER BY sexo
    ''')
    sexo_stats = cursor.fetchall()
    
    # Calcular totales para "Sexo"
    total_sexo = sum(stat['recuento'] for stat in sexo_stats)
    sexo_data = {
        'labels': [stat['sexo'] for stat in sexo_stats],
        'data': [stat['recuento'] for stat in sexo_stats],
        'percentages': [round((stat['recuento'] / total_sexo) * 100, 1) if total_sexo > 0 else 0 
                       for stat in sexo_stats]
    }
    
    # Estadísticas 4: Progreso por número de sesiones (culminó vs ongoing)
    cursor.execute('''
    SELECT 
        CASE WHEN sesion_numero = 17 THEN 'Completado' ELSE 'En Progreso' END as estado,
        COUNT(*) as recuento
    FROM inscripciones 
    WHERE inicio = 'Si'
    GROUP BY estado
''')
    progreso_stats = cursor.fetchall()
    
    # Calcular totales para "Progreso"
    total_progreso = sum(stat['recuento'] for stat in progreso_stats)
    progreso_data = {
        'labels': [stat['estado'] for stat in progreso_stats],
        'data': [stat['recuento'] for stat in progreso_stats],
        'percentages': [round((stat['recuento'] / total_progreso) * 100, 1) if total_progreso > 0 else 0 
                        for stat in progreso_stats]
    }
    
    # Estadísticas 5: Cambio promedio de peso para quienes desean bajar de peso
    cursor.execute('''
        SELECT 
            ROUND(AVG(peso_actual - peso_hoy), 2) as cambio_promedio,
            COUNT(*) as recuento
        FROM inscripciones 
        WHERE inicio = 'Si' 
        AND desea_bajar_peso = 'Si' 
        AND peso_actual IS NOT NULL 
        AND peso_hoy IS NOT NULL
    ''')
    cambio_peso_stats = cursor.fetchone()
    
    # Estadísticas para participantes que terminaron
    cursor.execute('''
        SELECT COUNT(*) as recuento, 
            ROUND(AVG(peso_actual - peso_hoy), 2) as cambio_promedio
        FROM inscripciones 
        WHERE inicio = 'Si' AND termino = 'Si'
        AND peso_actual IS NOT NULL AND peso_hoy IS NOT NULL
    ''')
    terminados_stats = cursor.fetchone()
    
    db.close()
    
    return render_template(
        'dashboard.html',
        inicio_stats=inicio_stats,
        inicio_data=inicio_data,
        general_stats=general_stats,
        sexo_stats=sexo_stats,
        sexo_data=sexo_data,
        progreso_stats=progreso_stats,
        progreso_data=progreso_data,
        cambio_peso_stats=cambio_peso_stats,
        terminados_stats=terminados_stats
    )

@app.route('/descargar_csv')
def descargar_csv():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM inscripciones ORDER BY nombres_apellidos")
    inscripciones = cursor.fetchall()
    db.close()

    # Crear un objeto StringIO para escribir el CSV
    csv_buffer = StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Escribir los encabezados
    if inscripciones:  # Check if there are any entries
        csv_writer.writerow(inscripciones[0].keys())  # Use the keys from the first row

    # Escribir los datos
    for inscripcion in inscripciones:
        csv_writer.writerow(inscripcion)

    # Crear la respuesta HTTP
    response = make_response(csv_buffer.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=inscripciones.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response

if __name__ == '__main__':
    app.run(debug=True)
                    