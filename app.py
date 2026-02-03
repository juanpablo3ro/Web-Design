from flask import Flask, render_template, request, jsonify
from flask_mail import Mail, Message
import sqlite3
import os
from dotenv import load_dotenv
import threading
from datetime import datetime

app = Flask(__name__)

load_dotenv()
# --- CONFIGURACIÓN DE FLASK-MAIL ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
# RECUERDA: Usa aquí tu "Contraseña de Aplicación" de 16 caracteres de Google
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD') 
app.config['MAIL_DEFAULT_SENDER'] = 'proditeamweb@gmail.com'

mail = Mail(app)

# --- 1. CONFIGURACIÓN DE BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('prodi_salud.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historias_clinicas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
            nombre TEXT, apellidos TEXT, edad INTEGER, sexo TEXT,
            email TEXT, 
            telefono TEXT, ciudad TEXT, pais TEXT,
            antecedentes TEXT, presion_sistolica INTEGER, presion_diastolica INTEGER,
            medicamento_presion TEXT, glucosa_ayunas INTEGER, medicamento_glucosa TEXT,
            hba1c REAL, colesterol_total INTEGER, trigliceridos INTEGER,
            colesterol_ldl INTEGER, colesterol_hdl INTEGER, medicamento_lipidos TEXT,
            peso_kg REAL, talla_cm REAL, perimetro_abdominal REAL, medicamento_peso TEXT,
            desea_bajar_peso TEXT, porcentaje_perdida TEXT, tiempo_perdida TEXT,
            habito_tabaquico TEXT, exposicion_humo TEXT, nivel_actividad TEXT,
            minutos_actividad_semana TEXT, raciones_frutas INTEGER, raciones_vegetales INTEGER,
            raciones_grano_entero INTEGER, raciones_pescado INTEGER, vasos_bebidas_azucaradas INTEGER,
            habitos_sal TEXT, frecuencia_lacteos TEXT, frecuencia_carnes TEXT,
            frecuencia_alcohol TEXT, cantidad_alcohol_dia TEXT, puntuacion_sueno INTEGER,
            ronca TEXT, circunferencia_cuello REAL, enfermedades_presentadas TEXT,
            escala_salud_hoy INTEGER, ansiedad_nervios TEXT, control_preocupacion TEXT,
            poco_interes TEXT, sentimiento_deprimido TEXT, nivel_optimismo INTEGER,
            nivel_pesimismo INTEGER, notas_medico TEXT, analisis_driver TEXT
        )
    ''')
    conn.commit()
    conn.close()

# --- 2. FUNCIONES DE CORREO ELECTRÓNICO ---
def enviar_email_al_equipo(data, resumen_salud):
    """Envía notificación interna con datos técnicos al equipo médico"""
    # Usamos el contexto de la app para que el hilo reconozca a Flask-Mail
    with app.app_context():
        try:
            subject = f"NUEVO REGISTRO: {data.get('nombre')} {data.get('apellidos')}"
            recipient = "proditeamweb@gmail.com"
            
            html_content = f"""
            <div style="font-family: sans-serif; max-width: 600px; border: 1px solid #ddd; padding: 20px;">
                <h2 style="color: #158082;">Aviso de Nuevo Paciente</h2>
                <p><strong>Nombre:</strong> {data.get('nombre')} {data.get('apellidos')}</p>
                <p><strong>Email:</strong> {data.get('email')}</p>
                <p><strong>Ciudad:</strong> {data.get('ciudad')}</p>
                <div style="background: #f4f4f4; padding: 15px; border-left: 4px solid #158082;">
                    <strong>Resumen Clínico Automático:</strong><br>
                    {resumen_salud}
                </div>
                <p>Revisar detalles completos en el Dashboard del sistema.</p>
            </div>
            """
            msg = Message(subject=subject, recipients=[recipient], html=html_content)
            mail.send(msg)
            print("Notificación enviada al equipo con éxito.")
        except Exception as e:
            print(f"Error al notificar al equipo: {e}")

def enviar_confirmacion_al_paciente(data):
    """Envía confirmación de cortesía al paciente sin datos médicos"""
    # Usamos el contexto de la app aquí también
    with app.app_context():
        try:
            email_paciente = data.get('email')
            if not email_paciente: return

            subject = "Confirmación de recepción - Cuestionario PRODI Salud"
            html_content = f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; text-align: center;">
                <h2 style="color: #158082;">¡Gracias por tu confianza, {data.get('nombre')}!</h2>
                <p>Hemos recibido exitosamente los datos de tu cuestionario de salud.</p>
                <p>Próximamente recibirás tu reporte detallado.</p>
            </div>
            """
            msg = Message(subject=subject, recipients=[email_paciente], html=html_content)
            mail.send(msg)
            print(f"Confirmación enviada al paciente: {email_paciente}")
        except Exception as e:
            print(f"Error al enviar confirmación al paciente: {e}")

# --- 3. RUTAS ---

@app.route('/')
def index():
    return render_template('cuestionario_general.html')

@app.route('/dashboard')
def dashboard():
    try:
        conn = sqlite3.connect('prodi_salud.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM historias_clinicas ORDER BY fecha_registro DESC")
        pacientes = cursor.fetchall()
        conn.close()
        return render_template('dashboard.html', pacientes=pacientes)
    except Exception as e:
        return f"Error al cargar el dashboard: {e}"
    
def guardar_en_db(datos_tupla):
    """Guarda los datos en la base de datos en background"""
    try:
        conn = sqlite3.connect('prodi_salud.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO historias_clinicas (
            nombre, apellidos, edad, sexo, email, telefono, ciudad, pais, antecedentes,
            presion_sistolica, presion_diastolica, medicamento_presion, glucosa_ayunas,
            medicamento_glucosa, hba1c, colesterol_total, trigliceridos, colesterol_ldl,
            colesterol_hdl, medicamento_lipidos, peso_kg, talla_cm, perimetro_abdominal,
            medicamento_peso, desea_bajar_peso, porcentaje_perdida, tiempo_perdida,
            habito_tabaquico, exposicion_humo, nivel_actividad, minutos_actividad_semana,
            raciones_frutas, raciones_vegetales, raciones_grano_entero, raciones_pescado,
            vasos_bebidas_azucaradas, habitos_sal, frecuencia_lacteos, frecuencia_carnes,
            frecuencia_alcohol, cantidad_alcohol_dia, puntuacion_sueno, ronca,
            circunferencia_cuello, enfermedades_presentadas, escala_salud_hoy,
            ansiedad_nervios, control_preocupacion, poco_interes, sentimiento_deprimido,
            nivel_optimismo, nivel_pesimismo, notas_medico, analisis_driver
        ) VALUES (''' + "?,"*53 + "?)", datos_tupla)
        
        conn.commit()
        conn.close()
        print("✓ Datos guardados en BD")
    except Exception as e:
        print(f"✗ Error guardando en BD: {e}")

@app.route('/submit_form', methods=['POST'])
def enviar():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se recibieron datos"}), 400

    # Lista de campos exactos según tu tabla historias_clinicas
    columnas = [
        "nombre", "apellidos", "edad", "sexo", "email", "telefono", "ciudad", "pais", "antecedentes",
        "presion_sistolica", "presion_diastolica", "medicamento_presion", "glucosa_ayunas",
        "medicamento_glucosa", "hba1c", "colesterol_total", "trigliceridos", "colesterol_ldl",
        "colesterol_hdl", "medicamento_lipidos", "peso_kg", "talla_cm", "perimetro_abdominal",
        "medicamento_peso", "desea_bajar_peso", "porcentaje_perdida", "tiempo_perdida",
        "habito_tabaquico", "exposicion_humo", "nivel_actividad", "minutos_actividad_semana",
        "raciones_frutas", "raciones_vegetales", "raciones_grano_entero", "raciones_pescado",
        "vasos_bebidas_azucaradas", "habitos_sal", "frecuencia_lacteos", "frecuencia_carnes",
        "frecuencia_alcohol", "cantidad_alcohol_dia", "puntuacion_sueno", "ronca",
        "circunferencia_cuello", "enfermedades_presentadas", "escala_salud_hoy",
        "ansiedad_nervios", "control_preocupacion", "poco_interes", "sentimiento_deprimido",
        "nivel_optimismo", "nivel_pesimismo", "notas_medico", "analisis_driver"
    ]

    # Mapeo de datos (asegúrate de que los nombres coincidan con los 'name' de tu HTML/JS)
    # Generar resumen de salud básico
    resumen_salud = f"Paciente: {data.get('nombre')}. Edad: {data.get('edad')}. Sexo: {data.get('sexo')}."
    
    datos_tupla = (
        data.get('nombre'), data.get('apellidos'), data.get('edad'), data.get('sexo'),
        data.get('email'), data.get('telefono'), data.get('ciudad'), data.get('pais'),
        ", ".join(data.get('antecedentes', [])) if isinstance(data.get('antecedentes'), list) else data.get('antecedentes'), 
        data.get('presion-sistolica'), data.get('presion-diastolica'), data.get('med-presion'), data.get('glucosa-ayunas'),
        data.get('med-glucosa'), data.get('hba1c'), data.get('colesterol-total'),
        data.get('trigliceridos'), data.get('colesterol-ldl'), data.get('colesterol-hdl'),
        data.get('med-lipidos'), data.get('peso'), data.get('talla'),
        data.get('perimetro-abdominal'), data.get('med-peso'), data.get('bajar-peso'),
        data.get('porcentaje-perdida'), data.get('tiempo-perdida'), data.get('habito-tabaquico'),
        data.get('exposicion-humo'), data.get('nivel-actividad'), data.get('minutos-actividad'),
        data.get('frutas'), data.get('vegetales'), data.get('grano-entero'),
        data.get('pescado'), data.get('bebidas-azucaradas'), 
        ", ".join(data.get('habitos-sal', [])) if isinstance(data.get('habitos-sal'), list) else data.get('habitos-sal'),
        data.get('frecuencia-lacteos'), data.get('frecuencia-carnes'), data.get('frecuencia-alcohol'),
        data.get('cantidad-alcohol'), data.get('calidad-sueno'), data.get('ronca'),
        data.get('circunferencia-cuello'), 
        ", ".join(data.get('enfermedades', [])) if isinstance(data.get('enfermedades'), list) else data.get('enfermedades'),
        data.get('escala-salud'), data.get('ansioso'), data.get('preocupacion'),
        data.get('interes'), data.get('deprimido'), data.get('optimismo'),
        data.get('pesimismo'), data.get('notas-medico'), resumen_salud
    )

    try:
        # Generar la query dinámicamente para evitar errores de comas o puntos
        placeholders = ", ".join(["?"] * len(columnas))
        query = f"INSERT INTO historias_clinicas ({', '.join(columnas)}) VALUES ({placeholders})"
        
        conn = sqlite3.connect('prodi_salud.db')
        cursor = conn.cursor()
        cursor.execute(query, datos_tupla)
        id_generado = cursor.lastrowid
        conn.commit()
        conn.close()
        print(f"✓ Guardado exitoso. ID: {id_generado}")

        # Ejecutar correos en hilos
        threading.Thread(target=enviar_email_al_equipo, args=(data, resumen_salud), daemon=True).start()
        threading.Thread(target=enviar_confirmacion_al_paciente, args=(data,), daemon=True).start()

        return jsonify({"status": "success", "id": id_generado}), 200

    except Exception as e:
        print(f"Error en proceso: {e}")
        return jsonify({"error": str(e)}), 500

# --- 1. VISTA PRINCIPAL DEL REPORTE ---
@app.route('/reporte/<int:p_id>')
def reporte_detalle(p_id):
    try:
        conn = sqlite3.connect('prodi_salud.db')
        conn.row_factory = sqlite3.Row # Esto es vital
        cursor = conn.cursor()
        
        # 1. Datos del paciente actual
        cursor.execute("SELECT * FROM historias_clinicas WHERE id = ?", (p_id,))
        paciente = cursor.fetchone()

        # 2. Lista para el selector lateral
        cursor.execute("SELECT id, nombre, apellidos FROM historias_clinicas ORDER BY nombre ASC")
        filas = cursor.fetchall()
        lista_nombres = [(r['id'], f"{r['nombre']} {r['apellidos']}") for r in filas]
        
        conn.close()

        if not paciente:
            return "Paciente no encontrado", 404

        return render_template('reporte_paciente.html', 
                               datos=paciente, 
                               inscripciones_nombres=lista_nombres)
    except Exception as e:
        return f"Error: {e}", 500

# --- 2. API PARA CARGAR DATOS (USADA POR EL JAVASCRIPT DEL REPORTE) ---
@app.route('/get_submission/<int:p_id>')
def get_submission(p_id):
    try:
        conn = sqlite3.connect('prodi_salud.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM historias_clinicas WHERE id = ?", (p_id,))
        p = cursor.fetchone()
        conn.close()
        
        if p:
            return jsonify(dict(p))
        return jsonify({"error": "No encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- NUEVOS ENDPOINTS PARA INTEGRACIÓN Y BUSQUEDA ---

@app.route('/api/all_participants')
def all_participants():
    try:
        conn = sqlite3.connect('prodi_salud.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, apellidos FROM historias_clinicas ORDER BY nombre ASC")
        filas = cursor.fetchall()
        conn.close()
        
        lista = [{"id": r["id"], "nombre_completo": f"{r['nombre']} {r['apellidos']}"} for r in filas]
        return jsonify(lista)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download_raw_data/<int:p_id>')
def download_raw_data(p_id):
    try:
        conn = sqlite3.connect('prodi_salud.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM historias_clinicas WHERE id = ?", (p_id,))
        p = cursor.fetchone()
        conn.close()
        
        if p:
            data = dict(p)
            response = jsonify(data)
            response.headers.set('Content-Disposition', 'attachment', filename=f'paciente_{p_id}.json')
            return response
        return jsonify({"error": "No encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/save_gemini_analysis', methods=['POST'])
def save_gemini_analysis():
    data = request.get_json()
    p_id = data.get('id')
    analysis = data.get('analysis')
    
    try:
        conn = sqlite3.connect('prodi_salud.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE historias_clinicas SET analisis_driver = ? WHERE id = ?", (analysis, p_id))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- 3. API PARA GUARDAR CAMBIOS ---
@app.route('/update_submission', methods=['POST'])
def update_submission():
    data = request.get_json()
    p_id = data.get('id')
    
    try:
        conn = sqlite3.connect('prodi_salud.db')
        cursor = conn.cursor()
        
        # Aquí actualizamos todos los campos editables que definimos en el HTML
        cursor.execute("""
            UPDATE historias_clinicas 
            SET nombre = ?, 
                notas_medico = ?,
                rec_actividad = ?,
                rec_tabaco = ?,
                rec_apnea = ?,
                rec_glucosa = ?,
                rec_lipidos = ?,
                diag_lipidos = ?
            WHERE id = ?
        """, (
            data.get('nombre'), 
            data.get('notas_medico'),
            data.get('rec_actividad'),
            data.get('rec_tabaco'),
            data.get('rec_apnea'),
            data.get('rec_glucosa'),
            data.get('rec_lipidos'),
            data.get('diag_lipidos'),
            p_id
        ))
        
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- 4. EJECUCIÓN DEL SERVIDOR (SIEMPRE AL FINAL) ---
if __name__ == '__main__':
    # Asegúrate de mantener tus rutas de /dashboard y /submit aquí arriba
    app.run(debug=True, port=5001)