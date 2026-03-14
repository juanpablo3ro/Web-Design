from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import re
from dotenv import load_dotenv
import threading
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # Permitir textos largos de Gemini
app.secret_key = os.getenv('SECRET_KEY', 'prodi_secret_key_2024')

load_dotenv()
# --- CONFIGURACIÓN DE FLASK-MAIL ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD') 
app.config['MAIL_DEFAULT_SENDER'] = 'proditeamweb@gmail.com'

mail = Mail(app)

# --- 1. CONFIGURACIÓN DE BASE DE DATOS (ACTUALIZADA) ---
def init_db():
    conn = sqlite3.connect('prodi_salud.db')
    cursor = conn.cursor()
    
    # Tabla Maestra (Historia Clínica Inicial)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historias_clinicas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
            nombre TEXT, apellidos TEXT, edad INTEGER, sexo TEXT,
            email TEXT, telefono TEXT, ciudad TEXT, pais TEXT,
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
            frecuencia_alcohol TEXT, cantidad_alcohol TEXT, puntuacion_sueno INTEGER,
            ronca TEXT, circunferencia_cuello REAL, enfermedades_presentadas TEXT,
            escala_salud_hoy INTEGER, ansiedad_nervios TEXT, control_preocupacion TEXT,
            poco_interes TEXT, sentimiento_deprimido TEXT, nivel_optimismo INTEGER,
            nivel_pesimismo INTEGER, notas_medico TEXT, analisis_driver TEXT,
            rec_actividad TEXT, rec_alcohol TEXT, rec_ansiedad TEXT, rec_apnea TEXT,
            rec_azucar TEXT, rec_carnes TEXT, rec_depresion TEXT, rec_frutas TEXT,
            rec_glucosa TEXT, rec_granos TEXT, rec_lacteos TEXT, rec_lipidos_cardio TEXT,
            rec_lipidos TEXT, rec_optimismo TEXT, rec_pasivo TEXT, rec_pescado TEXT,
            rec_pesimismo TEXT, rec_presion TEXT, rec_sodio TEXT, rec_tabaco TEXT,
            rec_vegetales TEXT, diag_lipidos TEXT
        )
    ''')

    # NUEVA TABLA: Seguimiento Digital Twin (Check-ins Semanales/Mensuales)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seguimiento_twin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER,
            fecha_checkin TEXT DEFAULT CURRENT_TIMESTAMP,
            tipo_checkin TEXT, -- 'semanal' o 'mensual'
            peso REAL,
            pasos_dia INTEGER,
            frutas INTEGER, vegetales INTEGER, granos INTEGER, pescado INTEGER, 
            azucar INTEGER, lacteos INTEGER, carnes_rojas INTEGER,
            puntuacion_sueno INTEGER,
            -- Campos Mensuales (opcionales en semanal)
            presion_sistolica INTEGER, presion_diastolica INTEGER,
            perimetro_cintura REAL, perimetro_cuello REAL,
            ansiedad_nervios TEXT, control_preocupacion TEXT,
            poco_interes TEXT, sentimiento_deprimido TEXT,
            nivel_optimismo INTEGER, nivel_pesimismo INTEGER,
            escala_salud_hoy INTEGER,
            analisis_ia_semanal TEXT, -- Para guardar lo que Gemini diga cada semana
            FOREIGN KEY (paciente_id) REFERENCES historias_clinicas (id)
        )
    ''')
    # NUEVA TABLA: Perfil Nutricional (Baseline Alimentario)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS perfil_nutricional (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER,
            deseo_bajar_peso TEXT,
            porcentaje_peso TEXT,
            vegetariano TEXT,
            consumo_leche_huevos TEXT,
            frecuencia_procesados TEXT,
            frecuencia_frituras TEXT,
            frecuencia_carnes_rojas TEXT,
            frecuencia_frutas_veg TEXT,
            frecuencia_legumbres TEXT,
            frecuencia_alcohol TEXT,
            frecuencia_bebidas_azucaradas TEXT,
            fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (paciente_id) REFERENCES historias_clinicas(id)
        )
    ''')
    # NUEVA TABLA: Usuarios (Login)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            paciente_id INTEGER,
            role TEXT DEFAULT 'paciente',
            FOREIGN KEY (paciente_id) REFERENCES historias_clinicas(id)
        )
    ''')
    conn.commit()
    conn.close()

# Inicializar DB al arrancar
init_db()

# --- MIDDLEWARE DE AUTENTICACIÓN ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- 3. RUTAS DE NAVEGACIÓN ---

# 1. LA HOME (El Launchpad)
@app.route('/')
def home():
    # Si ya está logueado, lo mandamos a su landing personalizada, si es paciente.
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return render_template('index.html')
        return redirect(url_for('landing_usuario'))
    return redirect(url_for('login'))

# --- RUTAS DE AUTENTICACION ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = sqlite3.connect('prodi_salud.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['email'] = user['email']
            session['paciente_id'] = user['paciente_id']
            session['role'] = user['role']
            
            if user['role'] == 'admin':
                return redirect(url_for('home'))
            return redirect(url_for('landing_usuario'))
        
        return render_template('login.html', error="Email o contraseña incorrectos")
    
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            return render_template('registro.html', error="Las contraseñas no coinciden")
            
        hashed_pw = generate_password_hash(password)
        
        conn = sqlite3.connect('prodi_salud.db')
        cursor = conn.cursor()
        
        try:
            # Primero ver si existe una historia clinica con ese email
            cursor.execute("SELECT id FROM historias_clinicas WHERE email = ?", (email,))
            paciente = cursor.fetchone()
            p_id = paciente[0] if paciente else None
            
            cursor.execute("INSERT INTO usuarios (email, password, paciente_id) VALUES (?, ?, ?)", 
                         (email, hashed_pw, p_id))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('registro.html', error="El email ya está registrado")
        except Exception as e:
            conn.close()
            return render_template('registro.html', error=str(e))
            
    return render_template('registro.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/perfil')
@login_required
def landing_usuario():
    # Landing page personalizada donde el usuario ve sus opciones
    p_id = session.get('paciente_id')
    if not p_id:
        # Si no tiene ID de paciente, lo redirigimos a completar su perfil
        return render_template('landing_usuario_vacio.html')
        
    conn = sqlite3.connect('prodi_salud.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM historias_clinicas WHERE id = ?", (p_id,))
    paciente = cursor.fetchone()
    conn.close()
    
    return render_template('landing_usuario.html', paciente=paciente)

@app.route('/cuestionario')
def cuestionario():
    return render_template('cuestionario_general.html')

# 3. LISTA DE PARTICIPANTES (Gestión)
@app.route('/lista_participantes')
def lista_participantes():
    # Esta es la tabla con todos los pacientes registrados
    conn = sqlite3.connect('prodi_salud.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM historias_clinicas ORDER BY fecha_registro DESC")
    pacientes = cursor.fetchall()
    conn.close()
    return render_template('lista_participantes.html', pacientes=pacientes)

# 4. FORMULARIO DE SEGUIMIENTO SEMANAL (Check-in)
@app.route('/seguimiento')
def seguimiento_semanal():
    # El formulario corto para que el paciente llene cada semana
    return render_template('seguimiento_semanal.html')

# 5. DASHBOARD DEL DIGITAL TWIN (Individual)
@app.route('/digital_twin/<int:p_id>')
def ver_gemelo(p_id):
    # Esta ruta recibe el ID del paciente (ej: /digital_twin/1)
    conn = sqlite3.connect('prodi_salud.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Obtenemos datos básicos del paciente
    cursor.execute("SELECT * FROM historias_clinicas WHERE id = ?", (p_id,))
    paciente = cursor.fetchone()
    
    # Obtenemos todos sus pesajes y pasos históricos
    cursor.execute("SELECT * FROM seguimiento_twin WHERE paciente_id = ? ORDER BY fecha_checkin DESC", (p_id,))
    historial = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    if paciente is None:
        return "Paciente no encontrado", 404
        
    return render_template('digital_twin.html', paciente=paciente, historial=historial)

# 6. PERFIL NUTRICIONAL (Baseline Alimentario)
@app.route('/perfil_nutricional')
def perfil_nutricional():
    # Esta ruta carga el nuevo cuestionario de preferencias alimentarias
    return render_template('cuestionario_nutricional.html')

# 7. Reporte Nutricional Dinámico
@app.route('/reporte_nutricional/<int:p_id>')
def reporte_nutricional(p_id):
    conn = sqlite3.connect('prodi_salud.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Obtener todos los datos del paciente
    cursor.execute("SELECT * FROM historias_clinicas WHERE id = ?", (p_id,))
    paciente_row = cursor.fetchone()
    
    if not paciente_row:
        conn.close()
        return "Paciente no encontrado.", 404
        
    paciente = dict(paciente_row)
    
    # 2. Obtener sus datos nutricionales (preferencias)
    cursor.execute("SELECT * FROM perfil_nutricional WHERE paciente_id = ?", (p_id,))
    nutricion_row = cursor.fetchone()
    
    nutricion = dict(nutricion_row) if nutricion_row else {}
    
    # Valores por defecto para campos de preferencias
    if 'vegetariano' not in nutricion: nutricion['vegetariano'] = "--"
    if 'saciedad_baseline' not in nutricion: nutricion['saciedad_baseline'] = "--"
    if 'preferencia_sabor' not in nutricion: nutricion['preferencia_sabor'] = "--"
    
    conn.close()
    
    # 3. Lógica de Cálculo de Métricas (Si no están en la DB)
    
    # Metas de Peso
    deseo = nutricion.get('deseo_bajar_peso') or paciente.get('desea_bajar_peso', 'No')
    nutricion['deseo_bajar_peso'] = deseo
    
    # Tiempo meses
    tiempo_str = paciente.get('tiempo_perdida') or "0 meses"
    match_meses = re.search(r'(\d+)', str(tiempo_str))
    tiempo_meses = int(match_meses.group(1)) if match_meses else 0
    nutricion['tiempo_meses'] = tiempo_meses
    
    # Porcentaje de peso a perder
    pct_str = nutricion.get('porcentaje_peso') or paciente.get('porcentaje_perdida') or "0%"
    match_pct = re.search(r'(\d+)', str(pct_str))
    pct_val = float(match_pct.group(1)) if match_pct else 0
    nutricion['porcentaje_peso'] = f"{pct_val}%"
    
    # Asegurar tipos numéricos para cálculos
    try:
        peso = float(paciente.get('peso_kg') or 0)
    except (ValueError, TypeError):
        peso = 0
        
    try:
        talla = float(paciente.get('talla_cm') or 0)
    except (ValueError, TypeError):
        talla = 0
        
    try:
        edad = int(paciente.get('edad') or 30)
    except (ValueError, TypeError):
        edad = 30
        
    sexo = str(paciente.get('sexo') or 'M').lower()
    
    if peso > 0:
        total_perder = round(peso * (pct_val / 100), 1)
        nutricion['total_perder_kg'] = total_perder
        nutricion['meta_kg'] = round(peso - total_perder, 1)
        if tiempo_meses > 0:
            nutricion['meta_mensual_kg'] = round(total_perder / tiempo_meses, 1)
        else:
            nutricion['meta_mensual_kg'] = 0
    else:
        nutricion['total_perder_kg'] = "--"
        nutricion['meta_kg'] = "--"
        nutricion['meta_mensual_kg'] = "--"
        
    # Macronutrientes (Mifflin-St Jeor)
    if peso > 0 and talla > 0:
        if sexo.startswith('f'): # Femenino
            bmr = (10 * peso) + (6.25 * talla) - (5 * edad) - 161
        else: # Masculino
            bmr = (10 * peso) + (6.25 * talla) - (5 * edad) + 5
            
        # Factor de actividad
        actividad = str(paciente.get('nivel_actividad', 'Poco Activo')).lower()
        if 'muy' in actividad: factor = 1.55
        elif 'moderada' in actividad: factor = 1.375
        else: factor = 1.2
        
        tdee = bmr * factor
        calorias_meta = int(tdee - 500) if deseo == 'Sí' else int(tdee)
        if calorias_meta < 1200: calorias_meta = 1200
        
        nutricion['calorias_diarias'] = calorias_meta
        nutricion['gramos_proteina'] = int((calorias_meta * 0.25) / 4)
        nutricion['gramos_carbohidratos'] = int((calorias_meta * 0.45) / 4)
        nutricion['gramos_grasa'] = int((calorias_meta * 0.30) / 9)
    else:
        nutricion['calorias_diarias'] = "--"
        nutricion['gramos_proteina'] = "--"
        nutricion['gramos_carbohidratos'] = "--"
        nutricion['gramos_grasa'] = "--"
        
    # Otros datos sugeridos
    nutricion['porciones_fruta'] = 3 if deseo == 'Sí' else 4
    nutricion['fruta_comentario_1'] = "Consuma la fruta entera para aprovechar la fibra."
    nutricion['fruta_comentario_2'] = "Evite jugos procesados con azúcar añadida."
    nutricion['fruta_comentario_3'] = "La meta ideal es variar los colores de las frutas semanalmente."
    
    return render_template('reporte_nutricional.html', paciente=paciente, nutricion=nutricion)

    
# --- 2. FUNCIONES DE CORREO ELECTRÓNICO ---
def enviar_email_al_equipo(data, resumen_salud):
    """Envía notificación interna con datos técnicos al equipo médico"""
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

# --- 4. Ruta para guardar el perfil nutricional ---
@app.route('/submit_nutricion', methods=['POST'])
def submit_nutricion():
    if request.method == 'POST':
        # 1. Obtener datos del formulario
        email = request.form.get('correo')
        
        # 2. Conectar a la base de datos
        conn = sqlite3.connect('prodi_salud.db')
        cursor = conn.cursor()
        
        try:
            # Buscamos el ID del paciente usando el correo
            cursor.execute("SELECT id FROM historias_clinicas WHERE email = ?", (email,))
            paciente = cursor.fetchone()
            
            if paciente:
                p_id = paciente[0]
                # 3. Insertar datos nutricionales
                cursor.execute("""
                    INSERT INTO perfil_nutricional (
                        paciente_id, deseo_bajar_peso, porcentaje_peso, saciedad_baseline,
                        preferencia_sabor, vegetariano, consumo_leche_huevos,
                        frecuencia_procesados, frecuencia_frituras, frecuencia_carnes_rojas,
                        frecuencia_frutas_veg, frecuencia_legumbres, frecuencia_alcohol,
                        frecuencia_bebidas_azucaradas
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p_id,
                    request.form.get('deseo_bajar_peso'),
                    request.form.get('porcentaje_peso'),
                    request.form.get('saciedad'), # El slider 1-10
                    request.form.get('sabor_preferencia'),
                    request.form.get('vegetariano'),
                    request.form.get('consumo_leche_huevos'),
                    request.form.get('procesados'),
                    request.form.get('frituras'),
                    request.form.get('carnes_rojas'),
                    request.form.get('frutas_verduras'),
                    request.form.get('legumbres'),
                    request.form.get('alcohol'),
                    request.form.get('bebidas_azucaradas')
                ))
                conn.commit()
                mensaje = "Perfil Nutricional guardado con éxito."
            else:
                mensaje = "Error: El correo no coincide con ningún paciente registrado."
                
        except Exception as e:
            mensaje = f"Error en la base de datos: {e}"
        finally:
            conn.close()
            
        return render_template('index.html', notification=mensaje)

# --- 3. NUEVAS RUTAS PARA EL DIGITAL TWIN ---

@app.route('/api/save_checkin', methods=['POST'])
def save_checkin():
    """Guarda un nuevo registro de seguimiento semanal o mensual"""
    data = request.get_json()
    p_id = data.get('paciente_id')
    
    if not p_id:
        return jsonify({"error": "ID de paciente requerido"}), 400

    try:
        conn = sqlite3.connect('prodi_salud.db')
        cursor = conn.cursor()
        
        # Construcción dinámica basada en los datos recibidos
        columnas = data.keys()
        placeholders = ", ".join(["?"] * len(columnas))
        query = f"INSERT INTO seguimiento_twin ({', '.join(columnas)}) VALUES ({placeholders})"
        
        cursor.execute(query, list(data.values()))
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "message": "Check-in guardado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/digital_twin/<int:p_id>')
def digital_twin_dashboard(p_id):
    """Renderiza la vista del Gemelo Digital para un paciente"""
    try:
        conn = sqlite3.connect('prodi_salud.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Obtener datos iniciales
        cursor.execute("SELECT * FROM historias_clinicas WHERE id = ?", (p_id,))
        paciente = cursor.fetchone()
        
        # 2. Obtener historial de check-ins
        cursor.execute("SELECT * FROM seguimiento_twin WHERE paciente_id = ? ORDER BY fecha_checkin DESC", (p_id,))
        historial = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return render_template('digital_twin.html', paciente=paciente, historial=historial)
    except Exception as e:
        return f"Error: {e}", 500


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

@app.route('/submit_form', methods=['POST'])
def enviar():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se recibieron datos"}), 400

    columnas = [
        "nombre", "apellidos", "edad", "sexo", "email", "telefono", "ciudad", "pais", "antecedentes",
        "presion_sistolica", "presion_diastolica", "medicamento_presion", "glucosa_ayunas",
        "medicamento_glucosa", "hba1c", "colesterol_total", "trigliceridos", "colesterol_ldl",
        "colesterol_hdl", "medicamento_lipidos", "peso_kg", "talla_cm", "perimetro_abdominal",
        "medicamento_peso", "desea_bajar_peso", "porcentaje_perdida", "tiempo_perdida",
        "habito_tabaquico", "exposicion_humo", "nivel_actividad", "minutos_actividad_semana",
        "raciones_frutas", "raciones_vegetales", "raciones_grano_entero", "raciones_pescado",
        "vasos_bebidas_azucaradas", "habitos_sal", "frecuencia_lacteos", "frecuencia_carnes",
        "frecuencia_alcohol", "cantidad_alcohol", "puntuacion_sueno", "ronca",
        "circunferencia_cuello", "enfermedades_presentadas", "escala_salud_hoy",
        "ansiedad_nervios", "control_preocupacion", "poco_interes", "sentimiento_deprimido",
        "nivel_optimismo", "nivel_pesimismo", "notas_medico", "analisis_driver"
    ]

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
        placeholders = ", ".join(["?"] * len(columnas))
        query = f"INSERT INTO historias_clinicas ({', '.join(columnas)}) VALUES ({placeholders})"
        
        conn = sqlite3.connect('prodi_salud.db')
        cursor = conn.cursor()
        cursor.execute(query, datos_tupla)
        id_generado = cursor.lastrowid
        
        # VINCULAR CON EL USUARIO (Si existe cuenta con ese email)
        email_paciente = data.get('email')
        if email_paciente:
            cursor.execute("UPDATE usuarios SET paciente_id = ? WHERE email = ?", (id_generado, email_paciente))
            if 'user_id' in session and session.get('email') == email_paciente:
                session['paciente_id'] = id_generado
                
        conn.commit()
        conn.close()

        threading.Thread(target=enviar_email_al_equipo, args=(data, resumen_salud), daemon=True).start()
        threading.Thread(target=enviar_confirmacion_al_paciente, args=(data,), daemon=True).start()

        return jsonify({"status": "success", "id": id_generado}), 200

    except Exception as e:
        print(f"Error en submit_form: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/reporte/<int:p_id>')
def reporte_detalle(p_id):
    try:
        conn = sqlite3.connect('prodi_salud.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM historias_clinicas WHERE id = ?", (p_id,))
        paciente = cursor.fetchone()

        cursor.execute("SELECT id, nombre, apellidos FROM historias_clinicas ORDER BY nombre ASC")
        filas = cursor.fetchall()
        lista_nombres = [(r['id'], f"{r['nombre']} {r['apellidos']}") for r in filas]
        conn.close()

        if not paciente:
            return "Paciente no encontrado", 404

        return render_template('reporte_paciente.html', datos=paciente, inscripciones_nombres=lista_nombres)
    except Exception as e:
        return f"Error: {e}", 500

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

@app.route('/update_submission', methods=['POST'])
def update_submission():
    """Endpoint dinámico para actualizar cualquier campo de la historia clínica"""
    data = request.get_json()
    p_id = data.get('id')
    if not p_id:
        return jsonify({"error": "ID de paciente requerido"}), 400
    
    # Extraer campos a actualizar (excluyendo el id)
    updates = {k: v for k, v in data.items() if k != 'id' and k != 'fecha_actualizacion'}
    
    if not updates:
        return jsonify({"message": "No hay campos para actualizar"}), 200

    try:
        conn = sqlite3.connect('prodi_salud.db')
        cursor = conn.cursor()
        
        # Validar qué columnas existen realmente en la tabla para evitar errores
        cursor.execute("PRAGMA table_info(historias_clinicas)")
        db_columns = [row[1] for row in cursor.fetchall()]
        
        filtered_updates = {k: v for k, v in updates.items() if k in db_columns}
        
        if not filtered_updates:
            return jsonify({"error": "Ninguno de los campos proporcionados existe en la base de datos"}), 400

        # Construir query dinámica
        set_clause = ", ".join([f"{k} = ?" for k in filtered_updates.keys()])
        values = list(filtered_updates.values())
        values.append(p_id)
        
        query = f"UPDATE historias_clinicas SET {set_clause} WHERE id = ?"
        
        cursor.execute(query, values)
        conn.commit()
        conn.close()
        return jsonify({"success": True, "updated_fields": list(filtered_updates.keys())})
    except Exception as e:
        print(f"Error en update_submission: {e}")
        return jsonify({"error": str(e)}), 500

# --- 4. EJECUCIÓN DEL SERVIDOR (SIEMPRE AL FINAL) ---
if __name__ == '__main__':
    # Asegúrate de mantener tus rutas de /dashboard y /submit aquí arriba
    app.run(debug=True, port=5001)