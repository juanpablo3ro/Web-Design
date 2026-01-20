from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)

# --- FUNCIÓN DE BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('prodi_salud.db')
    cursor = conn.cursor()
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
            frecuencia_alcohol TEXT, cantidad_alcohol_dia TEXT, puntuacion_sueno INTEGER,
            ronca TEXT, circunferencia_cuello REAL, enfermedades_presentadas TEXT,
            escala_salud_hoy INTEGER, ansiedad_nervios TEXT, control_preocupacion TEXT,
            poco_interes TEXT, sentimiento_deprimido TEXT, nivel_optimismo INTEGER,
            nivel_pesimismo INTEGER, notas_medico TEXT, analisis_driver TEXT
        )
    ''')
    conn.commit()
    conn.close()

# --- RUTAS ---

@app.route('/')
def index():
    return render_template('cuestionario_general.html')

@app.route('/submit_form', methods=['POST'])
def enviar():
    # IMPORTANTE: Tu JS envía JSON, por lo tanto usamos get_json()
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No se recibieron datos"}), 400

    # Extraer cálculos de salud generados por el JS
    calculos = data.get('calculos_salud', {})
    resumen_salud = f"IMC: {calculos.get('imc')} ({calculos.get('estado_nutricional')}). " \
                    f"Sueño: {calculos.get('calidad_sueno_evaluacion')}. " \
                    f"Ansiedad/Depresión: {calculos.get('sintomas_ansiedad')}/{calculos.get('sintomas_depresion')}."

    # Preparamos la tupla de datos para SQL (usando .get para evitar errores si falta un campo)
    datos_tupla = (
        data.get('nombre'),
        data.get('apellidos'),
        data.get('edad'),
        data.get('sexo'),
        data.get('email'),
        data.get('telefono'),
        data.get('ciudad'),
        data.get('pais'),
        ", ".join(data.get('antecedentes', [])),
        data.get('presion-sistolica'),
        data.get('presion-diastolica'),
        data.get('med-presion'),
        data.get('glucosa-ayunas'),
        data.get('med-glucosa'),
        data.get('hba1c'),
        data.get('colesterol-total'),
        data.get('trigliceridos'),
        data.get('colesterol-ldl'),
        data.get('colesterol-hdl'),
        data.get('med-lipidos'),
        data.get('peso'),
        data.get('talla'),
        data.get('perimetro-abdominal'),
        data.get('med-peso'),
        data.get('bajar-peso'),
        data.get('porcentaje-perdida'),
        data.get('tiempo-perdida'),
        data.get('habito-tabaquico'),
        data.get('exposicion-humo'),
        data.get('nivel-actividad'),
        data.get('minutos-actividad'),
        data.get('frutas'),
        data.get('vegetales'),
        data.get('grano-entero'),
        data.get('pescado'),
        data.get('bebidas-azucaradas'),
        ", ".join(data.get('habitos-sal', [])),
        data.get('frecuencia-lacteos'),
        data.get('frecuencia-carnes'),
        data.get('frecuencia-alcohol'),
        data.get('cantidad-alcohol'),
        data.get('calidad-sueno'),
        data.get('ronca'),
        data.get('circunferencia-cuello'),
        ", ".join(data.get('enfermedades', [])),
        data.get('escala-salud'),
        data.get('ansioso'),
        data.get('preocupacion'),
        data.get('interes'),
        data.get('deprimido'),
        data.get('optimismo'),
        data.get('pesimismo'),
        data.get('notas-medico'),
        resumen_salud # Se guarda en la columna analisis_driver
    )

    try:
        conn = sqlite3.connect('prodi_salud.db')
        cursor = conn.cursor()
        
        # Hay 54 columnas en total (incluyendo id y fecha que son automáticas)
        # Aquí insertamos 54 valores manuales (id/fecha se omiten o se dejan automáticos)
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
        
        id_generado = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Respondemos en JSON para que el JS pueda mostrar el mensaje de éxito
        return jsonify({"status": "success", "id": id_generado}), 200

    except Exception as e:
        print(f"Error en DB: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001)