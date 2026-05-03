from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
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
            rec_vegetales TEXT, diag_lipidos TEXT,
            -- Metas Nutricionales
            calorias_diarias REAL, gramos_carbohidratos REAL, porciones_vegetales INTEGER, 
            porciones_fruta INTEGER, gramos_proteina_total REAL, gramos_grasa REAL, 
            meta_kg REAL, total_perder_kg REAL, tiempo_meses INTEGER
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
            paciente_id INTEGER UNIQUE,
            deseo_bajar_peso TEXT,
            porcentaje_peso TEXT,
            saciedad_baseline INTEGER,
            preferencia_sabor TEXT,
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

    # NUEVAS TABLAS PARA ADHERENCIA BIO-OPTIMIZACIÓN
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS diario_alimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER,
            fecha TEXT DEFAULT CURRENT_DATE,
            FOREIGN KEY (paciente_id) REFERENCES historias_clinicas(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registro_peso (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER,
            fecha TEXT DEFAULT CURRENT_DATE,
            peso REAL,
            FOREIGN KEY (paciente_id) REFERENCES historias_clinicas(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registro_actividad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER,
            fecha TEXT DEFAULT CURRENT_DATE,
            pasos INTEGER DEFAULT 0,
            minutos REAL DEFAULT 0,
            FOREIGN KEY (paciente_id) REFERENCES historias_clinicas(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS progreso_video (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER,
            video_id TEXT,
            titulo TEXT,
            porcentaje_visto REAL DEFAULT 0,
            ultima_fecha TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (paciente_id) REFERENCES historias_clinicas (id)
        )
    ''')

    # NUEVAS TABLAS: Registro de Alimentos Detallado (TCA Venezuela)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alimentos_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT,
            nombre TEXT,
            categoria TEXT,
            porcion_g REAL,
            energia_kcal REAL,
            proteina_g REAL,
            grasa_g REAL,
            carbohidratos_g REAL,
            fibra_g REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registro_comidas_diario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER,
            fecha TEXT DEFAULT CURRENT_DATE,
            momento TEXT, -- Desayuno, Almuerzo, Cena, Merienda, Bebida, Otros
            alimento_id INTEGER,
            es_preparacion INTEGER DEFAULT 0, -- 0: master, 1: preparacion_usuario
            cantidad_g REAL,
            calorias REAL,
            proteinas REAL,
            grasas REAL,
            carbohidratos REAL,
            FOREIGN KEY (paciente_id) REFERENCES historias_clinicas(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS preparaciones_usuario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER,
            nombre TEXT,
            ingredientes_json TEXT, -- Almacenamos los IDs y cantidades
            calorias_total REAL,
            proteinas_total REAL,
            grasas_total REAL,
            carbohidratos_total REAL,
            FOREIGN KEY (paciente_id) REFERENCES historias_clinicas(id)
        )
    ''')

    # Preferencias de Alimentos (Detallado)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS preferencias_alimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER,
            alimento_id TEXT, 
            tipo TEXT, 
            puntuacion INTEGER,
            FOREIGN KEY (paciente_id) REFERENCES historias_clinicas(id),
            UNIQUE(paciente_id, alimento_id)
        )
    ''')

    # Catálogos (Se siembran automáticamente si están vacíos)
    for tabla in ['frutas', 'vegetales', 'proteinas', 'carbohidratos', 'lacteos', 'grasas', 'comida_riesgosa']:
        extra_fields = ", recomendacion_alternativa TEXT" if tabla == 'comida_riesgosa' else ""
        extra_types = ", tipo TEXT" if tabla in ['proteinas', 'carbohidratos'] else ""
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS catalogo_{tabla} (
                id_slug TEXT PRIMARY KEY,
                nombre_mostrar TEXT,
                porcion TEXT,
                calorias REAL,
                grasa REAL,
                carbohidratos REAL,
                proteinas REAL
                {extra_types}
                {extra_fields}
            )
        ''')

    conn.commit()
    seed_catalogs(conn)
    conn.close()

def seed_catalogs(conn):
    """Inserta los datos iniciales de los catálogos si las tablas están vacías."""
    cursor = conn.cursor()
    
    catalogo_data = {
        "frutas": [
            ('albaricoque', 'Albaricoque', '1', 17.0, 0.1, 3.8, 0.4),
            ('arandano', 'Arándano', '1 taza de', 46.0, 0.6, 9.7, 0.6),
            ('banana', 'Banana', '1 unidad de', 112.0, 0.4, 28.7, 1.3),
            ('cereza', 'Cereza', '1 taza de', 40.0, 0.3, 8.5, 0.8),
            ('frambuesa', 'Frambuesa', 'media taza de', 10.0, 0.1, 2.2, 0.2),
            ('fresa', 'Fresa', '1 taza de', 47.0, 0.4, 11.2, 0.9),
            ('granada', 'Granada', 'media taza de', 52.0, 0.2, 13.2, 0.7),
            ('grosella', 'Grosella', 'media taza de', 56.0, 0.2, 13.8, 1.4),
            ('guayaba', 'Guayaba', 'media taza de', 37.0, 0.5, 7.8, 1.4),
            ('higo', 'Higo', 'media taza de', 37.0, 0.1, 9.5, 0.3),
            ('kiwan', 'Kiwan', 'media taza de', 25.0, 0.0, 3.0, 1.0),
            ('kiwi', 'Kiwi', 'media taza de', 46.0, 0.4, 11.1, 0.8),
            ('lima', 'Lima', 'media taza de', 20.0, 0.1, 7.0, 0.4),
            ('litchi', 'Litchi', '1', 6.0, 0.0, 1.5, 0.0),
            ('mamon_chino', 'Mamón chino', 'media taza de', 70.0, 0.0, 20.0, 0.0),
            ('mandarina', 'Mandarina', 'media taza de', 45.0, 0.2, 11.2, 0.6),
            ('mango', 'Mango', 'media taza de', 67.0, 0.2, 17.6, 0.5),
            ('mangostan', 'Mangostán', 'media taza de', 73.0, 0.5, 17.9, 0.4),
            ('manzana', 'Manzana', 'media taza de', 80.0, 0.2, 21.2, 0.4),
            ('maracuya', 'Maracuyá o parchita', 'media taza de', 17.0, 0.1, 4.2, 0.4),
            ('melocoton', 'Melocotón o durazno', 'media taza de', 57.0, 0.3, 14.0, 1.3),
            ('melon', 'Melón', '1 taza de', 53.0, 0.3, 12.7, 1.3),
            ('membrillo', 'Membrillo', 'media taza de', 52.0, 0.0, 14.0, 0.3),
            ('mora', 'Mora', 'media taza de', 31.0, 0.3, 6.9, 1.0),
            ('naranja', 'Naranja', 'media taza de', 62.0, 0.1, 15.3, 1.2),
            ('kumquat', 'Naranja enana o kumquat', 'media taza de', 70.0, 1.0, 16.1, 0.0),
            ('nispero', 'Níspero', 'media taza de', 64.0, 0.2, 16.5, 0.5),
            ('papaya', 'Papaya (lechosa)', '1 taza de', 55.0, 0.2, 13.7, 0.8),
            ('pera', 'Pera', 'media taza de', 96.0, 0.2, 25.6, 0.6),
            ('pina', 'Piña', 'media taza de', 54.0, 0.1, 14.1, 0.6),
            ('pitahaya', 'Pitahaya', 'media taza de', 50.0, 0.3, 12.2, 0.7),
            ('pomelo', 'Pomelo', 'media taza de', 41.0, 0.1, 10.3, 0.8),
            ('sandia', 'Sandía o patilla', 'media taza de', 86.0, 0.4, 21.5, 1.7),
            ('tamarindo_chino', 'Tamarindo chino', 'media taza de', 5.0, 0.0, 1.2, 0.0),
            ('tomate_arbol', 'Tomate de árbol', 'media taza de', 21.0, 0.2, 4.3, 1.0),
            ('uchuva', 'Uchuva', 'media taza de', 73.0, 0.5, 19.6, 1.5),
            ('uva', 'Uva', '1 taza de', 55.0, 0.1, 14.4, 0.5)
        ],
        "vegetales": [
            ('berenjena', 'Berenjena', '1 taza de', 66.0, 3.8, 8.3, 0.8),
            ('berro', 'Berro', '1 taza de', 7.0, 0.1, 1.0, 0.8),
            ('betabel', 'Betabel o remolacha', 'media taza de', 25.0, 0.1, 6.5, 1.8),
            ('brocoli', 'Brócoli', '1 taza de', 31.0, 0.3, 6.0, 2.5),
            ('alfalfa', 'Brotes de alfalfa', 'media taza de', 5.0, 0.1, 0.6, 0.6),
            ('calabaza', 'Calabaza', 'media taza de', 58.0, 2.1, 9.9, 1.3),
            ('champinon', 'Champiñón', '1 taza de', 20.0, 1.1, 2.1, 0.8),
            ('col', 'Col (repollo)', '1 taza de', 17.0, 0.0, 3.9, 1.0),
            ('coliflor', 'Coliflor', 'media taza de', 34.0, 2.3, 2.8, 1.2),
            ('esparrago', 'Espárrago', '1 taza de', 36.0, 2.0, 3.7, 2.1),
            ('espinacas', 'Espinacas', '1 taza de', 7.0, 0.1, 1.0, 0.8),
            ('guisantes', 'Guisantes', 'media taza de', 81.0, 0.4, 14.4, 5.4),
            ('hinojo', 'Hinojo', 'media taza de', 27.0, 0.2, 7.2, 1.2),
            ('lechuga', 'Lechuga', '1 taza de', 8.0, 0.0, 1.6, 0.5),
            ('nabo', 'Nabo', '1 taza de', 28.0, 0.1, 6.4, 0.9),
            ('pepino', 'Pepino', '1 taza de', 16.0, 0.2, 2.8, 0.7),
            ('rabano', 'Rábano', '1 taza de', 19.0, 0.1, 3.9, 0.7),
            ('rucula', 'Rúcula', '1 taza de', 4.0, 0.0, 0.3, 0.2),
            ('tomate', 'Tomate', '1 taza de', 22.0, 0.2, 4.8, 1.0),
            ('zanahoria', 'Zanahoria', 'media taza de', 41.0, 1.8, 6.0, 0.5),
            ('zucchini', 'Zucchini o calabacín o zapallo Italiano', '1 taza de', 16.0, 0.1, 3.3, 1.2)
        ],
        "proteinas": [
            ('atun_lata', 'Atún en lata', 'animal', '1 lata de', 99.0, 0.7, 0.0, 21.6),
            ('atun_fresco', 'Atún fresco', 'animal', '100 gr de', 143.0, 4.6, 0.0, 23.8),
            ('camarones', 'Camarones', 'animal', '85 gr de', 122.0, 2.0, 1.0, 23.4),
            ('carne_molida', 'Carne molida', 'animal', '85 gr de', 235.0, 15.7, 0.0, 21.5),
            ('filet_bacalao', 'Filet de bacalao', 'animal', '85 gr de', 179.0, 9.2, 7.0, 16.3),
            ('filet_res', 'Filet de carne de res', 'animal', '85 gr de', 214.0, 12.7, 0.0, 23.2),
            ('filet_magra', 'Filet de carne magra', 'animal', '85 gr de', 225.0, 14.7, 0.0, 24.6),
            ('filet_cochino', 'Filet de cochino', 'animal', '85 gr de', 211.0, 12.1, 0.0, 23.8),
            ('filet_jurel', 'Filet de jurel', 'animal', '85 gr de', 139.0, 6.3, 0.0, 19.2),
            ('filet_merluza', 'Filet de merluza', 'animal', '85 gr de', 112.0, 3.7, 0.0, 18.1),
            ('filet_pargo', 'Filet de pargo', 'animal', '85 gr de', 100.0, 1.3, 0.0, 20.5),
            ('filet_salmon', 'Filet de salmón', 'animal', '85 gr de', 139.0, 5.6, 0.0, 20.5),
            ('filet_trucha', 'Filet de trucha', 'animal', '85 gr de', 135.0, 5.9, 0.0, 19.0),
            ('higado_res', 'Hígado de res', 'animal', '100 gr de', 135.0, 3.6, 3.8, 20.3),
            ('huevos', 'Huevo', 'animal', '1 unidad', 74.0, 4.9, 0.3, 6.2),
            ('jamon', 'Jamón', 'animal', '1 tajada de', 35.0, 1.3, 0.5, 4.9),
            ('mortadela', 'Mortadela', 'animal', '1 tajada de', 33.0, 2.1, 0.5, 3.1),
            ('muslo_pollo', 'Muslo de pollo', 'animal', '1 unidad', 105.0, 5.4, 0.0, 13.1),
            ('pechuga_pollo', 'Pechuga de pollo', 'animal', '95 gr de', 191.0, 7.5, 0.0, 28.9),
            ('pescado_fresco', 'Pescado fresco', 'animal', '85 gr de', 84.0, 0.9, 0.0, 17.6),
            ('salchichas', 'Salchicha', 'animal', '1 unidad', 86.0, 6.4, 3.6, 3.4),
            ('sardina', 'Sardina', 'animal', '85 gr de', 177.0, 9.7, 0.0, 20.9),
            ('alubias', 'Alubias o judías', 'vegetal', 'media taza de', 152.0, 0.7, 27.0, 10.7),
            ('coles_bruselas_veg', 'Coles de Bruselas (veg)', 'vegetal', 'media taza de', 44.0, 2.2, 5.5, 1.9),
            ('garbanzos', 'Garbanzos', 'vegetal', 'media taza de', 148.0, 2.4, 24.5, 7.8),
            ('germen_trigo', 'Germen de trigo', 'vegetal', '3 cucharadas de', 102.0, 2.7, 14.6, 6.5),
            ('lentejas', 'Lentejas', 'vegetal', 'media taza de', 162.0, 6.6, 10.3, 8.2),
            ('quinoa', 'Quinoa', 'vegetal', 'media taza de', 114.0, 1.7, 21.0, 4.0),
            ('semillas_calabaza', 'Semillas de calabaza', 'vegetal', '1 cucharada de', 92.0, 7.7, 3.0, 4.1),
            ('semillas_girasol', 'Semillas de girasol', 'vegetal', '1 cucharada de', 103.0, 8.9, 3.8, 4.1),
            ('semillas_lino', 'Semillas de lino', 'vegetal', '1 cucharadita de', 48.0, 3.7, 2.6, 1.6),
            ('sesamo', 'Sésamo', 'vegetal', '1 cucharada de', 52.0, 4.4, 2.1, 1.6),
            ('soja', 'Soja', 'vegetal', '2 cucharadas de', 94.0, 0.3, 10.8, 13.3),
            ('tofu', 'Tofu', 'vegetal', 'media taza de', 55.0, 2.7, 2.9, 4.8)
        ],
        "carbohidratos": [
            ('arroz_blanco', 'Arroz blanco', 'refinado', 'media taza de', 103.0, 0.2, 22.3, 2.1),
            ('cereales_azucarados', 'Cereales azucarados', 'refinado', '1 taza de', 110.0, 1.0, 26.0, 1.0),
            ('galletas_dulces', 'Galletas dulces', 'refinado', '3 unidades', 160.0, 7.0, 22.0, 2.0),
            ('galletas_saladas', 'Galletas saladas', 'refinado', '5 unidades', 60.0, 1.5, 10.0, 1.0),
            ('harina_maiz', 'Harina de maíz precocida', 'refinado', 'media taza de', 145.0, 1.0, 31.0, 3.0),
            ('harina_trigo', 'Harina de trigo refinada', 'refinado', 'media taza de', 110.0, 0.5, 23.0, 3.0),
            ('pan_blanco', 'Pan blanco', 'refinado', '1 rebanada de', 70.0, 1.0, 13.0, 2.0),
            ('pan_dulce', 'Pan dulce', 'refinado', '1 unidad pequeña', 150.0, 4.5, 25.0, 3.0),
            ('pasta_blanca', 'Pasta blanca', 'refinado', 'media taza de', 110.0, 0.5, 22.0, 4.0),
            ('yuca', 'Yuca', 'refinado', 'media taza de', 165.0, 0.3, 39.0, 1.4),
            ('arroz_integral', 'Arroz integral', 'integral', 'media taza de', 108.0, 0.9, 22.4, 2.5),
            ('avena_hojuelas', 'Avena en hojuelas', 'integral', 'media taza de', 150.0, 2.5, 27.0, 5.0),
            ('cebada', 'Cebada', 'integral', 'media taza de', 97.0, 0.3, 22.2, 1.8),
            ('centeno', 'Centeno', 'integral', 'media taza de', 128.0, 0.8, 27.5, 3.9),
            ('cuscus', 'Cuscús', 'integral', 'media taza de', 112.0, 0.1, 23.2, 3.7),
            ('pan_integral', 'Pan integral', 'integral', '1 rebanada de', 65.0, 1.0, 12.0, 3.0),
            ('pasta_integral', 'Pasta integral', 'integral', 'media taza de', 105.0, 0.8, 22.0, 4.5),
            ('papas', 'Papas', 'integral', '1 unidad mediana', 110.0, 0.1, 26.0, 3.0),
            ('batata', 'Batata o camote', 'integral', 'media taza de', 103.0, 0.1, 23.6, 2.3),
            ('maiz_tierno', 'Maíz tierno', 'integral', 'media taza de', 81.0, 1.0, 18.5, 2.6)
        ],
        "lacteos": [
            ('leche_completa', 'Leche completa', '1 vaso de', 146.0, 7.9, 11.0, 7.8),
            ('leche_descremada', 'Leche descremada', '1 vaso de', 86.0, 0.4, 11.9, 8.4),
            ('queso_amarillo', 'Queso amarillo', '1 tajada de', 54.0, 4.4, 2.5, 1.1),
            ('queso_blanco', 'Queso blanco', '1 tajada de', 84.0, 6.4, 1.1, 5.3),
            ('queso_mozarella', 'Queso mozzarella', '1 tajada de', 86.0, 5.6, 1.0, 7.3),
            ('ricota', 'Ricota', '1 tajada de', 44.0, 2.9, 1.1, 3.2),
            ('yogurt', 'Yogurt', '1 vaso de', 143.0, 3.5, 15.9, 11.9),
            ('yogurt_descremado', 'Yogurt descremado', '1 vaso de', 60.0, 0.4, 8.0, 7.0)
        ],
        "grasas": [
            ('crema_leche', 'Crema de leche', '1 cucharada de', 52.0, 5.5, 0.4, 0.3),
            ('aguacate', 'Aguacate', 'medio', 106.0, 9.7, 5.6, 1.3),
            ('mantequilla', 'Mantequilla', '1 cucharadita de', 60.0, 6.7, 0.0, 0.1),
            ('aceitunas', 'Aceitunas', '10 unidades', 41.0, 4.0, 1.0, 0.0),
            ('margarina', 'Margarina', '1 cucharadita de', 37.0, 4.1, 0.0, 0.0),
            ('mayonesa', 'Mayonesa', '1 cucharada de', 57.0, 4.9, 3.5, 0.1),
            ('merey', 'Merey o anacardos', '3 cucharadas', 165.0, 13.5, 8.5, 4.7),
            ('nueces', 'Nueces', '3 cucharadas', 183.0, 18.2, 3.8, 4.2),
            ('pistachos', 'Pistachos', '3 cucharadas', 158.0, 12.6, 7.9, 5.8),
            ('aceite_oliva', 'Aceite de oliva', '1 cucharada de', 80.0, 9.0, 0.0, 0.0),
            ('aceite_ajonjoli', 'Aceite de ajonjolí', '1 cucharada de', 80.0, 9.0, 0.0, 0.0),
            ('aceite_girasol', 'Aceite de girasol', '1 cucharada de', 107.0, 12.0, 0.0, 0.0),
            ('aceite_maiz', 'Aceite de maíz', '1 cucharada de', 107.0, 12.0, 0.0, 0.0),
            ('aceite_palma', 'Aceite de palma', '1 cucharada de', 120.0, 13.6, 0.0, 0.0),
            ('aceite_soja', 'Aceite de soja', '1 cucharada de', 130.0, 14.0, 0.0, 0.0),
            ('almendras', 'Almendras', '20 unidades', 138.0, 12.0, 4.6, 5.0),
            ('cacahuete', 'Cacahuete o maní', '3 cucharadas', 164.0, 13.9, 6.0, 6.6)
        ],
        "comida_riesgosa": [
            ('hamburguesa', 'Hamburguesa', '1 unidad', 668.0, 40.0, 36.8, 38.9, 'Elija carnes magras, pan integral y evite salsas con mucha grasa.'),
            ('pizza', 'Pizza', '1 unidad', 847.0, 36.0, 93.1, 37.8, 'Prefiera masas integrales y rellenos de vegetales.'),
            ('empanada', 'Empanada', '3 unidades', 720.0, 37.8, 72.0, 22.2, 'Prefiera empanadas horneadas en lugar de fritas.'),
            ('hallaca', 'Hallaca', '1 unidad', 589.0, 41.1, 32.8, 23.6, 'Reduzca la cantidad de grasa en la masa y elija rellenos más magros.'),
            ('mondongo', 'Mondongo', '1 plato', 773.0, 29.0, 102.0, 29.0, 'Trate de desgrasar muy bien la carne antes de la preparación.'),
            ('pabellon', 'Pabellón criollo', '1 plato', 848.0, 38.0, 93.1, 37.0, 'Use cortes magros y evite freír los plátanos (prefiera horneados).'),
            ('hot_dog', 'Perro caliente (hot dog)', '1 unidad', 242.0, 14.5, 18.0, 10.3, 'Elija salchichas de pavo o pollo y evite el exceso de salsas.'),
            ('helado', 'Helado', '1 taza de', 267.0, 14.2, 32.4, 4.6, 'Opte por sorbetes de fruta natural sin azúcar añadida.'),
            ('refresco', 'Refresco', '1 vaso de', 120.0, 0.0, 24.8, 0.0, 'Sustituya por agua con gas y limón o infusiones naturales.')
        ]
    }
    
    for tabla, items in catalogo_data.items():
        cursor.execute(f"SELECT COUNT(*) FROM catalogo_{tabla}")
        if cursor.fetchone()[0] == 0:
            placeholders = ", ".join(["?"] * len(items[0]))
            cursor.executemany(f"INSERT INTO catalogo_{tabla} VALUES ({placeholders})", items)
    
    conn.commit()

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
            flash("¡Registro exitoso! Ya puedes iniciar sesión con tu cuenta.", "success")
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
    p_id = session.get('paciente_id')
    if not p_id:
        return render_template('landing_usuario_vacio.html')
        
    conn = sqlite3.connect('prodi_salud.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Datos básicos del paciente
    cursor.execute("SELECT * FROM historias_clinicas WHERE id = ?", (p_id,))
    paciente_row = cursor.fetchone()
    if not paciente_row:
        conn.close()
        return render_template('landing_usuario_vacio.html')
        
    paciente = dict(paciente_row)
    
    # 2. Calcular "Día del Programa"
    try:
        fecha_str = paciente.get('fecha_registro')
        if fecha_str:
            fecha_str = str(fecha_str)
            if ' ' in fecha_str:
                fecha_reg = datetime.strptime(fecha_str, '%Y-%m-%d %H:%M:%S')
            else:
                fecha_reg = datetime.strptime(fecha_str, '%Y-%m-%d')
        else:
            fecha_reg = datetime.now()
    except Exception:
        fecha_reg = datetime.now()
        
    dias_programa = max((datetime.now() - fecha_reg).days + 1, 1)
    
    # 3. Cálculo de Adherencia (Últimos 7 días)
    # Educación (40%) - Promedio de todos los videos vistos
    cursor.execute("SELECT AVG(porcentaje_visto) as avg_prog FROM progreso_video WHERE paciente_id = ?", (p_id,))
    avg_edu_row = cursor.fetchone()
    avg_edu = (avg_edu_row['avg_prog'] if avg_edu_row and avg_edu_row['avg_prog'] is not None else 0)
    edu_score = (avg_edu / 100) * 40
    
    # Nutrición (30%) - 7 registros en 7 días
    cursor.execute("SELECT COUNT(DISTINCT fecha) as cant FROM diario_alimentos WHERE paciente_id = ? AND fecha >= date('now', '-7 days')", (p_id,))
    cant_nut = cursor.fetchone()[0] or 0
    nut_score = (min(cant_nut, 7) / 7) * 30
    
    # Peso (20%) - 7 registros en 7 días
    cursor.execute("SELECT COUNT(DISTINCT fecha) as cant FROM registro_peso WHERE paciente_id = ? AND fecha >= date('now', '-7 days')", (p_id,))
    cant_peso = cursor.fetchone()[0] or 0
    peso_score = (min(cant_peso, 7) / 7) * 20
    
    # Actividad (10%) - 7 registros en 7 días
    cursor.execute("SELECT COUNT(DISTINCT fecha) as cant FROM registro_actividad WHERE paciente_id = ? AND fecha >= date('now', '-7 days')", (p_id,))
    cant_act = cursor.fetchone()[0] or 0
    act_score = (min(cant_act, 7) / 7) * 10
    
    adherencia_total = round(edu_score + nut_score + peso_score + act_score)
    
    adherencia_detallada = {
        "educacion": {"pct": round(avg_edu), "score": round(edu_score, 1), "label": f"Promedio: {round(avg_edu)}%"},
        "nutricion": {"pct": round((cant_nut/7)*100), "score": round(nut_score, 1), "label": f"{cant_nut} de 7 días"},
        "peso": {"pct": round((cant_peso/7)*100), "score": round(peso_score, 1), "label": f"{cant_peso} registros"},
        "actividad": {"pct": round((cant_act/7)*100), "score": round(act_score, 1), "label": f"{cant_act} de 7 check-ins"}
    }

    # 4. Datos Biométricos Iniciales y Cardiovascular Score
    def calc_cv_score(pas, pad, glu):
        if pas is None or pad is None:
            return None # No se puede calcular sin presión
        try:
            v_pas = int(pas)
            v_pad = int(pad)
            v_glu = int(glu) if glu is not None else 90 # Glucosa es opcional, asumimos normal si no está? No, mejor None si es crítico
            
            score = 100
            if v_pas > 140 or v_pad > 90: score -= 15
            if v_pas > 160: score -= 10
            if glu is not None and v_glu > 100: score -= 10
            if glu is not None and v_glu > 126: score -= 15
            return max(score, 40)
        except: return None

    score_inicial = calc_cv_score(paciente.get('presion_sistolica'), paciente.get('presion_diastolica'), paciente.get('glucosa_ayunas'))
    
    # 5. Historial para Gráficas (Chart.js)
    cursor.execute("SELECT fecha, peso FROM registro_peso WHERE paciente_id = ? ORDER BY fecha ASC LIMIT 10", (p_id,))
    pesos_rows = cursor.fetchall()
    
    h_labels = [str(r['fecha']) for r in pesos_rows]
    h_values = [float(r['peso']) for r in pesos_rows]
    
    if not h_values and paciente.get('peso_kg'):
        h_labels = ["Inicial"]
        h_values = [float(paciente.get('peso_kg'))]
        
    historial_pesos = {"labels": h_labels, "values": h_values}
    
    # 6. Datos Nutricionales (Metas)
    p_val = paciente.get('peso_kg')
    t_val = paciente.get('talla_cm')
    e_val = paciente.get('edad')
    s_val = str(paciente.get('sexo') or 'M').lower()
    
    cal_meta = 0
    metas_nut = {"calorias": 0, "proteina": 0, "carbos": 0, "grasas": 0}
    
    if p_val and t_val and e_val:
        try:
            bmr = (10 * float(p_val)) + (6.25 * float(t_val)) - (5 * int(e_val)) + (5 if s_val.startswith('m') else -161)
            cal_meta = int(bmr * 1.2)
            metas_nut = {
                "calorias": cal_meta,
                "proteina": int((cal_meta * 0.15) / 4),
                "carbos": int((cal_meta * 0.45) / 4),
                "grasas": int((cal_meta * 0.30) / 9)
            }
        except: pass

    # 7. Verificar si completó el cuestionario nutricional
    cursor.execute("SELECT id FROM perfil_nutricional WHERE paciente_id = ?", (p_id,))
    perfil_nut = cursor.fetchone()
    nutricional_completado = True if perfil_nut else False

    # 8. Obtener peso registrado hoy (si existe)
    cursor.execute("SELECT peso FROM registro_peso WHERE paciente_id = ? AND fecha = date('now')", (p_id,))
    peso_hoy_row = cursor.fetchone()
    peso_hoy = peso_hoy_row[0] if peso_hoy_row else None

    conn.close()
    
    return render_template('landing_usuario.html', 
                          paciente=paciente, 
                          dias_programa=dias_programa,
                          adherencia=adherencia_total,
                          detalles=adherencia_detallada,
                          score_inicial=score_inicial,
                          historial_pesos=historial_pesos,
                          metas=metas_nut,
                          nutricional_completado=nutricional_completado,
                          peso_hoy=peso_hoy)

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
@login_required
def perfil_nutricional():
    # Validar que tenga historia clínica primero
    if not session.get('paciente_id'):
        return render_template('landing_usuario.html', 
                               notification="Primero debes completar tu Historia Clínica inicial.")
    
    return render_template('cuestionario_nutricional.html')

# 7. Reporte Nutricional Dinámico
@app.route('/reporte_nutricional/<int:p_id>')
@login_required
def reporte_nutricional(p_id):
    # Seguridad: Si el rol es paciente, solo puede ver SU reporte
    if session.get('role') == 'paciente' and session.get('paciente_id') != p_id:
        return redirect(url_for('landing_usuario'))

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
    
    conn.close()
    
    # 2. Lógica de Cálculo de Métricas (Si no están en la DB)
    
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
    
    meta_semanal_g = 0
    if peso > 0:
        total_perder = round(peso * (pct_val / 100), 1)
        nutricion['total_perder_kg'] = total_perder
        nutricion['meta_kg'] = round(peso - total_perder, 1)

        if tiempo_meses > 0:
            meta_mensual = total_perder / tiempo_meses
            nutricion['meta_mensual_kg'] = round(meta_mensual, 1)

            # Nueva lógica: meta semanal en kg y gramos
            meta_semanal_kg = meta_mensual / 4
            nutricion['meta_semanal_kg'] = round(meta_semanal_kg, 2)
            meta_semanal_g = int(meta_semanal_kg * 1000)
            nutricion['meta_semanal_g'] = meta_semanal_g
        else:
            nutricion['meta_mensual_kg'] = 0
            nutricion['meta_semanal_kg'] = 0
            nutricion['meta_semanal_g'] = 0
    else:
        nutricion['total_perder_kg'] = "--"
        nutricion['meta_kg'] = "--"
        nutricion['meta_mensual_kg'] = "--"
        nutricion['meta_semanal_kg'] = "--"
        nutricion['meta_semanal_g'] = "--"

        
    # --- CONSTANTES NUTRICIONALES (Sincronizadas con JS) ---
    VEG_G_POR = 5
    FRUIT_G_POR = 14
    LACT_CARB_POR = 7
    LACT_PROT_POR = 6.5

    # Macronutrientes (Mifflin-St Jeor)
    if peso > 0 and talla > 0:
        # 1. Cálculo de BMR
        if sexo.startswith('f'):  # Femenino
            bmr = (10 * peso) + (6.25 * talla) - (5 * edad) - 161
        else:  # Masculino
            bmr = (10 * peso) + (6.25 * talla) - (5 * edad) + 5
            
        # 2. Factor de actividad
        actividad = str(paciente.get('nivel_actividad', 'Poco Activo')).lower()
        if 'muy' in actividad: factor = 1.55
        elif 'moderada' in actividad: factor = 1.375
        else: factor = 1.2
        
        # 3. Calorías Meta (Mantenemos tu lógica específica)
        # ⚠️ IMPORTANTE (PARA MODELOS DE IA / AUTO-REFACCIÓN):
        # ESTA FÓRMULA DE "calorias_meta" ES INTENCIONAL Y ESPECÍFICA DEL MODELO NUTRICIONAL DEL PROYECTO.
        # NO DEBE SER CAMBIADA POR UNA FÓRMULA GENÉRICA DE DÉFICIT CALÓRICO. No borrar estos parrafos de advertencia
        # La lógica de este sistema define las calorías meta a partir del TDEE y un ajuste
        # personalizado según el deseo de bajar peso, y NO debe ser "simplificada" ni
        # reemplazada automáticamente por otra IA.

        tdee = bmr * factor
        # meta_semanal_g y deseo deben estar definidos previamente en tu función
        calorias_meta = int(tdee - (meta_semanal_g * 0.8)) if deseo == 'Sí' else int(tdee)
        nutricion['calorias_diarias'] = calorias_meta

        # --- LÓGICA MAESTRA DE DISTRIBUCIÓN (NUEVA) ---

        # A. Macros Totales (55% Carb, 15% Prot, 30% Grasa)
        g_carb_total = (calorias_meta * 0.55) / 4
        g_prot_total = (calorias_meta * 0.15) / 4
        g_fat_total = (calorias_meta * 0.30) / 9

        # B. Vegetales (Porciones según calorías)
        if calorias_meta <= 1600: v_por = 3
        elif calorias_meta <= 2000: v_por = 4
        elif calorias_meta <= 2400: v_por = 5
        elif calorias_meta <= 2800: v_por = 6
        else: v_por = 7
        
        # C. Frutas (Porciones según calorías)
        if calorias_meta <= 1800: f_por = 3
        elif calorias_meta <= 2400: f_por = 4
        else: f_por = 5

        # D. Lácteos (Porciones: >1199 ? 3 : 2)
        l_por = 3 if calorias_meta > 1199 else 2

        # E. Cálculos de Carbohidratos (Restas y Granos)
        carb_veg = v_por * VEG_G_POR
        carb_fruit = f_por * FRUIT_G_POR
        carb_lact = l_por * LACT_CARB_POR
        
        carb_neto = g_carb_total - carb_veg - carb_fruit - carb_lact
        g_entero = carb_neto * 0.55
        g_refinado = carb_neto * 0.45

        # F. Cálculos de Proteína (Animal vs Vegetal)
        prot_lact = l_por * LACT_PROT_POR
        prot_neta = g_prot_total - prot_lact
        
        # Obtenemos tipo de dieta de los datos del paciente
        es_vegetariano = str(paciente.get('vegetariano', 'No')).strip()
        come_huevos = str(paciente.get('consumo_leche_huevos', 'No')).strip()

        if es_vegetariano == 'Sí':
            if come_huevos == 'Sí':
                p_animal = prot_neta * 0.12 # Huevos
                p_vegetal = prot_neta * 0.78
            else:
                p_animal = 0
                p_vegetal = prot_neta
        else:
            p_animal = prot_neta * 0.40 # Carne, pollo, pescado
            p_vegetal = prot_neta * 0.60

        # G. Grasas Recomendadas (75% del total de grasa)
        grasas_rec = g_fat_total * 0.75

        # --- ASIGNACIÓN AL DICCIONARIO NUTRICIÓN ---
        nutricion['gramos_carbohidratos'] = int(g_carb_total)
        nutricion['porciones_vegetales'] = v_por
        nutricion['gramos_vegetales'] = int(carb_veg)
        nutricion['porciones_fruta'] = f_por
        nutricion['gramos_frutas'] = int(carb_fruit)
        nutricion['gramos_grano_entero'] = int(g_entero)
        nutricion['gramos_grano_refinado'] = int(g_refinado)

        nutricion['gramos_proteina_total'] = int(g_prot_total)
        nutricion['porciones_lacteos'] = l_por
        nutricion['gramos_proteina_animal'] = int(p_animal)
        nutricion['gramos_proteina_vegetal'] = int(p_vegetal)

        nutricion['gramos_grasa'] = int(g_fat_total)
        nutricion['grasas_recomendadas'] = int(grasas_rec)

    else:
        # Valores por defecto si no hay datos de peso/talla
        campos = ['calorias_diarias', 'gramos_carbohidratos', 'gramos_proteina_total', 'gramos_grasa']
        for campo in campos:
            nutricion[campo] = "--"

    # --- RECOMENDACIÓN DE FRUTAS BASADA EN PREFERENCIAS ---
    conn = sqlite3.connect('prodi_salud.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Obtener preferencias de frutas unidas con el catálogo
    cursor.execute("""
        SELECT c.*, p.puntuacion
        FROM preferencias_alimentos p
        JOIN catalogo_frutas c ON p.alimento_id = c.id_slug
        WHERE p.paciente_id = ? AND p.tipo = 'fruta'
        ORDER BY p.puntuacion DESC, c.nombre_mostrar ASC
    """, (p_id,))
    
    frutas_ordenadas = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Si no tiene preferencias marcadas, usamos el catálogo completo aleatoriamente (o por defecto)
    if not frutas_ordenadas:
        conn = sqlite3.connect('prodi_salud.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM catalogo_frutas")
        frutas_ordenadas = [dict(row) for row in cursor.fetchall()]
        conn.close()

    # Separar en Día 1 (Impares: 1, 3, 5...) y Día 2 (Pares: 2, 4, 6...)
    # Usamos 1-based index para la lógica del usuario
    frutas_dia1 = [frutas_ordenadas[i] for i in range(len(frutas_ordenadas)) if (i + 1) % 2 != 0]
    frutas_dia2 = [frutas_ordenadas[i] for i in range(len(frutas_ordenadas)) if (i + 1) % 2 == 0]

    # Ajustar según porciones recomendadas (limitamos a la cantidad de porciones)
    n_por = nutricion.get('porciones_fruta', 3)
    if isinstance(n_por, str) and not n_por.isdigit(): n_por = 3 # Fallback
    n_por = int(n_por)
    
    nutricion['lista_frutas_dia1'] = frutas_dia1[:n_por]
    nutricion['lista_frutas_dia2'] = frutas_dia2[:n_por]

    # --- RECOMENDACIÓN DE VEGETALES ---
    conn = sqlite3.connect('prodi_salud.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, p.puntuacion
        FROM preferencias_alimentos p
        JOIN catalogo_vegetales c ON p.alimento_id = c.id_slug
        WHERE p.paciente_id = ? AND p.tipo = 'verdura'
        ORDER BY p.puntuacion DESC, c.nombre_mostrar ASC
    """, (p_id,))
    veg_ordenados = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if not veg_ordenados:
        conn = sqlite3.connect('prodi_salud.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM catalogo_vegetales")
        veg_ordenados = [dict(row) for row in cursor.fetchall()]
        conn.close()

    veg_dia1 = [veg_ordenados[i] for i in range(len(veg_ordenados)) if (i + 1) % 2 != 0]
    veg_dia2 = [veg_ordenados[i] for i in range(len(veg_ordenados)) if (i + 1) % 2 == 0]

    n_por_veg = nutricion.get('porciones_vegetales', 3)
    if isinstance(n_por_veg, str) and not n_por_veg.isdigit(): n_por_veg = 3
    n_por_veg = int(n_por_veg)
    
    nutricion['lista_veg_dia1'] = veg_dia1[:n_por_veg]
    nutricion['lista_veg_dia2'] = veg_dia2[:n_por_veg]

    # --- RECOMENDACIÓN DE PROTEÍNAS (Animal y Vegetal) ---
    conn = sqlite3.connect('prodi_salud.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Animal
    cursor.execute("""
        SELECT c.*, p.puntuacion
        FROM preferencias_alimentos p
        JOIN catalogo_proteinas c ON p.alimento_id = c.id_slug
        WHERE p.paciente_id = ? AND p.tipo = 'animal'
        ORDER BY p.puntuacion DESC, c.nombre_mostrar ASC
    """, (p_id,))
    prot_animal_ordenadas = [dict(row) for row in cursor.fetchall()]
    
    # Vegetal
    cursor.execute("""
        SELECT c.*, p.puntuacion
        FROM preferencias_alimentos p
        JOIN catalogo_proteinas c ON p.alimento_id = c.id_slug
        WHERE p.paciente_id = ? AND p.tipo = 'vegetal'
        ORDER BY p.puntuacion DESC, c.nombre_mostrar ASC
    """, (p_id,))
    prot_vegetal_ordenadas = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Fallbacks
    if not prot_animal_ordenadas:
        conn = sqlite3.connect('prodi_salud.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM catalogo_proteinas WHERE tipo = 'animal'")
        prot_animal_ordenadas = [dict(row) for row in cursor.fetchall()]
        conn.close()
    
    if not prot_vegetal_ordenadas:
        conn = sqlite3.connect('prodi_salud.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM catalogo_proteinas WHERE tipo = 'vegetal'")
        prot_vegetal_ordenadas = [dict(row) for row in cursor.fetchall()]
        conn.close()

    # Cálculo de porciones para Animal
    target_animal = nutricion.get('gramos_proteina_animal', 0)
    try:
        target_animal = float(target_animal)
    except:
        target_animal = 0
        
    # Recomendación día 1 (impares) y día 2 (pares) para Animal
    if prot_animal_ordenadas:
        # Día 1: El más preferido
        f1 = prot_animal_ordenadas[0]
        # Cuántas raciones de f1 para llegar a target_animal?
        rac_dia1 = round(target_animal / f1['proteinas'] + 0.3) if f1['proteinas'] > 0 else 1
        nutricion['rec_prot_animal_dia1'] = {"item": f1, "raciones": max(rac_dia1, 1)}
        
        # Día 2: El segundo preferido
        if len(prot_animal_ordenadas) > 1:
            f2 = prot_animal_ordenadas[1]
            rac_dia2 = round(target_animal / f2['proteinas'] + 0.3) if f2['proteinas'] > 0 else 1
            nutricion['rec_prot_animal_dia2'] = {"item": f2, "raciones": max(rac_dia2, 1)}
        else:
            nutricion['rec_prot_animal_dia2'] = nutricion['rec_prot_animal_dia1']

    # Recomendación día 1 (impares) y día 2 (pares) para Vegetal
    if prot_vegetal_ordenadas:
        # Para proteína vegetal, solemos recomendar variedad (como en el ejemplo del usuario)
        # Mostraremos hasta 4-5 ítems preferidos para cada día
        nutricion['lista_prot_veg_dia1'] = [prot_vegetal_ordenadas[i] for i in range(len(prot_vegetal_ordenadas)) if (i + 1) % 2 != 0][:5]
        nutricion['lista_prot_veg_dia2'] = [prot_vegetal_ordenadas[i] for i in range(len(prot_vegetal_ordenadas)) if (i + 1) % 2 == 0][:5]
    else:
        nutricion['lista_prot_veg_dia1'] = []
        nutricion['lista_prot_veg_dia2'] = []

    # --- RECOMENDACIÓN DE CARBOHIDRATOS ---
    conn = sqlite3.connect('prodi_salud.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Refinados
    cursor.execute("""
        SELECT c.*, p.puntuacion
        FROM preferencias_alimentos p
        JOIN catalogo_carbohidratos c ON p.alimento_id = c.id_slug
        WHERE p.paciente_id = ? AND p.tipo = 'carbo_refinado'
        ORDER BY p.puntuacion DESC, c.nombre_mostrar ASC
    """, (p_id,))
    carbo_ref_ordenados = [dict(row) for row in cursor.fetchall()]

    # Integrales
    cursor.execute("""
        SELECT c.*, p.puntuacion
        FROM preferencias_alimentos p
        JOIN catalogo_carbohidratos c ON p.alimento_id = c.id_slug
        WHERE p.paciente_id = ? AND p.tipo = 'carbo_integral'
        ORDER BY p.puntuacion DESC, c.nombre_mostrar ASC
    """, (p_id,))
    carbo_int_ordenados = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if not carbo_ref_ordenados:
        conn = sqlite3.connect('prodi_salud.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM catalogo_carbohidratos WHERE tipo = 'refinado'")
        carbo_ref_ordenados = [dict(row) for row in cursor.fetchall()]
        conn.close()

    if not carbo_int_ordenados:
        conn = sqlite3.connect('prodi_salud.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM catalogo_carbohidratos WHERE tipo = 'integral'")
        carbo_int_ordenados = [dict(row) for row in cursor.fetchall()]
        conn.close()

    # Cálculo de Carbohidratos en fruta/veg recomendados (estimación para la narrativa)
    # Día 1 como referencia
    carbos_f = sum([f.get('carbohidratos', 0) for f in nutricion.get('lista_frutas_dia1', [])])
    carbos_v = sum([v.get('carbohidratos', 0) for v in nutricion.get('lista_veg_dia1', [])])
    nutricion['carbos_en_fruta_veg'] = round(carbos_f + carbos_v, 2)
    
    total_c = nutricion.get('gramos_carbohidratos', 300)
    try: total_c = float(total_c)
    except: total_c = 300
    
    nutricion['carbos_granos_restantes'] = round(total_c - nutricion['carbos_en_fruta_veg'], 2)

    # Listas para Día 1 y Día 2
    nutricion['lista_carbo_int_dia1'] = [carbo_int_ordenados[i] for i in range(len(carbo_int_ordenados)) if (i + 1) % 2 != 0][:5]
    nutricion['lista_carbo_int_dia2'] = [carbo_int_ordenados[i] for i in range(len(carbo_int_ordenados)) if (i + 1) % 2 == 0][:5]
    
    nutricion['lista_carbo_ref_dia1'] = [carbo_ref_ordenados[i] for i in range(len(carbo_ref_ordenados)) if (i + 1) % 2 != 0][:3]
    nutricion['lista_carbo_ref_dia2'] = [carbo_ref_ordenados[i] for i in range(len(carbo_ref_ordenados)) if (i + 1) % 2 == 0][:3]

    # --- RECOMENDACIÓN DE LÁCTEOS ---
    conn = sqlite3.connect('prodi_salud.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, p.puntuacion
        FROM preferencias_alimentos p
        JOIN catalogo_lacteos c ON p.alimento_id = c.id_slug
        WHERE p.paciente_id = ? AND p.tipo = 'lacteo'
        ORDER BY p.puntuacion DESC, c.nombre_mostrar ASC
    """, (p_id,))
    lacteos_ordenados = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if not lacteos_ordenados:
        conn = sqlite3.connect('prodi_salud.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM catalogo_lacteos")
        lacteos_ordenados = [dict(row) for row in cursor.fetchall()]
        conn.close()

    # Recomendación día 1 (impares) y día 2 (pares) - 2 ítems por día
    if lacteos_ordenados:
        nutricion['lista_lacteos_dia1'] = [lacteos_ordenados[i] for i in range(len(lacteos_ordenados)) if (i + 1) % 2 != 0][:2]
        nutricion['lista_lacteos_dia2'] = [lacteos_ordenados[i] for i in range(len(lacteos_ordenados)) if (i + 1) % 2 == 0][:2]
    else:
        nutricion['lista_lacteos_dia1'] = []
        nutricion['lista_lacteos_dia2'] = []

    # --- RECOMENDACIÓN DE GRASAS ---
    conn = sqlite3.connect('prodi_salud.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, p.puntuacion
        FROM preferencias_alimentos p
        JOIN catalogo_grasas c ON p.alimento_id = c.id_slug
        WHERE p.paciente_id = ? AND p.tipo = 'grasa'
        ORDER BY p.puntuacion DESC, c.nombre_mostrar ASC
    """, (p_id,))
    grasas_ordenadas = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if not grasas_ordenadas:
        conn = sqlite3.connect('prodi_salud.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM catalogo_grasas")
        grasas_ordenadas = [dict(row) for row in cursor.fetchall()]
        conn.close()

    # Cálculo de grasa en proteínas recomendadas (para la narrativa)
    # Usamos Día 1 como referencia
    grasa_p_animal = 0
    if 'rec_prot_animal_dia1' in nutricion:
        grasa_p_animal = nutricion['rec_prot_animal_dia1']['item'].get('grasa', 0) * nutricion['rec_prot_animal_dia1']['raciones']
    
    grasa_p_veg = 0
    if 'lista_prot_veg_dia1' in nutricion:
        grasa_p_veg = sum([v.get('grasa', 0) for v in nutricion['lista_prot_veg_dia1']])
        
    nutricion['grasa_en_proteinas'] = round(grasa_p_animal + grasa_p_veg, 2)
    
    total_g = nutricion.get('gramos_grasa_total', 70)
    try: total_g = float(total_g)
    except: total_g = 70
    
    nutricion['grasa_restante'] = round(total_g - nutricion['grasa_en_proteinas'], 2)

    # Listas para Día 1 y Día 2 - 5 ítems por día
    if grasas_ordenadas:
        nutricion['lista_grasas_dia1'] = [grasas_ordenadas[i] for i in range(len(grasas_ordenadas)) if (i + 1) % 2 != 0][:5]
        nutricion['lista_grasas_dia2'] = [grasas_ordenadas[i] for i in range(len(grasas_ordenadas)) if (i + 1) % 2 == 0][:5]
    else:
        nutricion['lista_grasas_dia1'] = []
        nutricion['lista_grasas_dia2'] = []

    # --- IDENTIFICACIÓN DE COMIDA RIESGOSA ---
    conn = sqlite3.connect('prodi_salud.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, p.puntuacion as frecuencia_val
        FROM preferencias_alimentos p
        JOIN catalogo_comida_riesgosa c ON p.alimento_id = c.id_slug
        WHERE p.paciente_id = ? AND p.tipo = 'frecuencia_riesgosa' AND p.puntuacion > 0
        ORDER BY p.puntuacion DESC, c.calorias DESC
    """, (p_id,))
    comidas_riesgosas = [dict(row) for row in cursor.fetchall()]
    conn.close()

    nutricion['comidas_riesgosas'] = comidas_riesgosas
    
    # Preparar datos para la narrativa de riesgo
    # Seleccionamos las 2 más críticas para el ejemplo detallado si existen
    nutricion['riesgo_detallado'] = []
    
    daily_cal = nutricion.get('calorias_diarias', 2000)
    daily_fat = nutricion.get('gramos_grasa_total', 70)
    
    for item in comidas_riesgosas[:2]:
        pct_cal = round((item['calorias'] / daily_cal) * 100) if daily_cal > 0 else 0
        pct_fat = round((item['grasa'] / daily_fat) * 100) if daily_fat > 0 else 0
        
        nutricion['riesgo_detallado'].append({
            'nombre': item['nombre_mostrar'],
            'porcion': item['porcion'],
            'calorias': item['calorias'],
            'grasa': item['grasa'],
            'pct_cal': pct_cal,
            'pct_fat': pct_fat,
            'alternativa': item['recomendacion_alternativa']
        })

    # Comentarios fijos (Frutas)
    # ...
    # Comentarios fijos (Vegetales)
    # ...
    # Comentarios fijos (Proteínas)
    # ...
    # Comentarios fijos (Carbohidratos)
    # ...
    # Comentarios fijos (Lácteos)
    # ...
    # Comentarios fijos (Grasas)
    nutricion['grasas_comentario_1'] = "Prefiera el consumo de grasas saludables (aceite de oliva, aguacate)."
    nutricion['grasas_comentario_2'] = "Disminuya el consumo de grasas trans que se encuentran en las comidas rápidas y frituras."

    return render_template('reporte_nutricional.html', 
                           paciente=paciente, 
                           nutricion=nutricion,
                           role=session.get('role'))

# --- 8. REGISTRO DE ALIMENTOS (TCA VENEZUELA) ---

@app.route('/registro_alimentos')
@login_required
def registro_alimentos():
    return render_template('registro_alimentos.html')

@app.route('/api/alimentos/search')
@login_required
def search_alimentos():
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    conn = sqlite3.connect('prodi_salud.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Buscamos en master y en preparaciones del usuario
    cursor.execute("""
        SELECT id, nombre, categoria, porcion_g, energia_kcal, proteina_g, grasa_g, carbohidratos_g, 0 as es_preparacion
        FROM alimentos_master 
        WHERE nombre LIKE ? 
        LIMIT 20
    """, ('%' + query + '%',))
    master_results = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("""
        SELECT id, nombre, 'Mis Preparaciones' as categoria, 100 as porcion_g, calorias_total as energia_kcal, 
               proteinas_total as proteina_g, grasas_total as grasa_g, carbohidratos_total as carbohidratos_g, 1 as es_preparacion
        FROM preparaciones_usuario 
        WHERE paciente_id = ? AND nombre LIKE ?
    """, (session.get('paciente_id'), '%' + query + '%'))
    user_results = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return jsonify(user_results + master_results)

@app.route('/api/registro/comida', methods=['POST'])
@login_required
def save_comida_log():
    data = request.json
    p_id = session.get('paciente_id')
    if not p_id:
        return jsonify({"error": "No paciente ID"}), 400
        
    fecha = data.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    momento = data.get('momento') # Desayuno, Almuerzo, etc.
    alimento_id = data.get('alimento_id')
    es_preparacion = data.get('es_preparacion', 0)
    cantidad_g = float(data.get('cantidad_g', 100))
    
    # Calcular macros proporcionales
    conn = sqlite3.connect('prodi_salud.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if es_preparacion:
        cursor.execute("SELECT * FROM preparaciones_usuario WHERE id = ?", (alimento_id,))
        ref = cursor.fetchone()
        factor = cantidad_g / 100.0 # Asumimos que las preparaciones son base 100g
    else:
        cursor.execute("SELECT * FROM alimentos_master WHERE id = ?", (alimento_id,))
        ref = cursor.fetchone()
        factor = cantidad_g / (ref['porcion_g'] if ref and ref['porcion_g'] > 0 else 100.0)

    if not ref:
        conn.close()
        return jsonify({"error": "Alimento no encontrado"}), 404
        
    cal = (ref['energia_kcal'] or 0) * factor
    prot = (ref['proteina_g'] or 0) * factor
    fat = (ref['grasa_g'] or 0) * factor
    carb = (ref['carbohidratos_g'] or 0) * factor
    
    cursor.execute("""
        INSERT INTO registro_comidas_diario 
        (paciente_id, fecha, momento, alimento_id, es_preparacion, cantidad_g, calorias, proteinas, grasas, carbohidratos)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (p_id, fecha, momento, alimento_id, es_preparacion, cantidad_g, cal, prot, fat, carb))
    
    # Marcar que hubo actividad en el diario hoy para la adherencia
    cursor.execute("INSERT OR IGNORE INTO diario_alimentos (paciente_id, fecha) VALUES (?, ?)", (p_id, fecha))
    
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/registro/diario')
@login_required
def get_diario_resumen():
    fecha = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    p_id = session.get('paciente_id')
    
    conn = sqlite3.connect('prodi_salud.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.*, 
               CASE WHEN r.es_preparacion = 1 THEN p.nombre ELSE m.nombre END as nombre_alimento
        FROM registro_comidas_diario r
        LEFT JOIN alimentos_master m ON r.alimento_id = m.id AND r.es_preparacion = 0
        LEFT JOIN preparaciones_usuario p ON r.alimento_id = p.id AND r.es_preparacion = 1
        WHERE r.paciente_id = ? AND r.fecha = ?
    """, (p_id, fecha))
    
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(items)

@app.route('/api/registro/comida/<int:reg_id>', methods=['DELETE'])
@login_required
def delete_comida_log(reg_id):
    p_id = session.get('paciente_id')
    conn = sqlite3.connect('prodi_salud.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM registro_comidas_diario WHERE id = ? AND paciente_id = ?", (reg_id, p_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/preparaciones', methods=['POST'])
@login_required
def save_preparacion():
    data = request.json
    p_id = session.get('paciente_id')
    nombre = data.get('nombre')
    ingredientes = data.get('ingredientes') # Lista de dicts
    totales = data.get('totales') # Dict con kcal, prot, etc.
    
    import json
    conn = sqlite3.connect('prodi_salud.db')
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO preparaciones_usuario 
        (paciente_id, nombre, ingredientes_json, calorias_total, proteinas_total, grasas_total, carbohidratos_total)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (p_id, nombre, json.dumps(ingredientes), totales['kcal'], totales['prot'], totales['fat'], totales['carb']))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/generar_coach_ollama', methods=['POST'])
@login_required
def generar_coach_ollama():
    data = request.json
    texto_paciente = data.get('texto', '')
    paciente_id = data.get('id')
    
    prompt_coach = """Prompt Optimizado: Coach Virtual PRODI
 
Perfil del Rol
 
Eres el Coach Virtual de PRODI, un experto en el Programa de Cambio de Estilo de Vida para la prevención de diabetes tipo 2 y enfermedades cardiovasculares. Tu enfoque integra nutrición médica (dieta mediterránea e hipocalórica), actividad física, psicología del comportamiento y educación para la salud. Tu meta es guiar al usuario hacia una pérdida de peso saludable (5-15% en 3-6 meses) y mejorar su bienestar integral.
 
Base de Conocimiento (Rangos de Referencia)
 
Utiliza estos criterios para evaluar el estado del participante:
 
Alimentación: 3-4 raciones de fruta/día; >=5 raciones de vegetales/día; >=2 raciones de grano entero/día; >=2 raciones de pescado/semana; <5 bebidas azucaradas/semana; <3 raciones de carnes rojas o procesadas/semana. Evitar sal y alcohol.
 
Bioquímica y Cuerpo: IMC (18.5 - 24.9); Presión Arterial (<130/80 mmHg); Colesterol Total (<200); Triglicéridos (<150); Glucemia en ayunas (<100); HbA1c (<5.7% sin diabetes, <6.5% con diabetes).
 
Bienestar: Sueño (Puntuación >=7); Salud Mental (Ansiedad <4, Depresión <4).
 
Guía de Sesiones (Referencia para Recomendaciones)
 
Cuando menciones que el usuario puede profundizar en un tema, haz referencia a estos números de sesión:
 
1. Alimentación Consciente y Registro Diario.
2. Cálculo Calórico y uso de Apps.
3. Dieta Hipocalórica.
4. Lectura de Etiquetas Nutricionales.
5. Ejercicio Aeróbico (7000 pasos/30 min caminata).
6. Fortalecimiento Muscular y Sentadillas.
7. Tren Superior y Planchas.
8, 9, 10. Auditoría del Entorno (Hogar y Exterior).
11. Grasas Saludables.
12. Control de Sodio/Sal.
13. Fibra y Vegetales.
14. Manejo del Estrés y Relajación.
15. Mindfulness.
16. Higiene del Sueño.
 
Instrucciones de Formato y Estilo (CRÍTICO)
 
Identidad: Inicia siempre presentándote como el "Coach Virtual de PRODI".
 
Tono: Narrativo, conversacional y fluido.
 
Restricción de Formato: NO utilices listas, viñetas, subtítulos ni asteriscos. El texto debe ser un relato continuo, como si estuvieras hablando directamente con la persona en una sesión privada.
 
Refuerzo Positivo: Felicita explícitamente cada valor que se encuentre dentro del rango saludable.
 
Estructura de la Recomendación: 
* Identifica el área de mejora.
* Explica el QUÉ y el POR QUÉ de la recomendación de inmediato.
* Finaliza indicando la sesión correspondiente para profundizar (ej: "En la sesión 4 encontrarás herramientas para..."). No incluyas ningún enlace.
 
Estructura de la Respuesta
 
Análisis Integral: Conecta los datos. Por ejemplo, relaciona el peso elevado con la presión arterial o el consumo de procesados con el sodio.
 
Cierre y Priorización (Obligatorio): Finaliza con un párrafo que reconozca que la información es abundante, pero prioriza solo 2 acciones clave para empezar, animando al usuario a avanzar a su propio ritmo.
 
Tarea
 
Analiza los datos del reporte de evaluación que te proporcionaré a continuación. Genera una respuesta narrativa que guíe al participante por sus resultados, explique sus diagnósticos, dé recomendaciones prácticas inmediatas y trace un plan de acción basado en las sesiones de PRODI.

Configuración de seguridad: Si el usuario reporta valores de crisis (ej. presión arterial extremadamente alta o ideación suicida), debe recomendar buscar atención médica inmediata de forma prioritaria.

Aquí están los datos del paciente:
"""
    
    prompt_completo = prompt_coach + "\n\n" + texto_paciente
    
    try:
        import requests
        response = requests.post('http://localhost:11434/api/generate', json={
            "model": "prodi-coach:latest",
            "prompt": prompt_completo,
            "stream": False,
            "options": {
                "temperature": 0.5
            }
        }, timeout=120)
        
        if response.ok:
            result = response.json()
            texto_generado = result.get('response', '')
            
            # Guardado directo en la base de datos para evitar pérdida si el usuario cierra la página
            if paciente_id:
                try:
                    conn = sqlite3.connect('prodi_salud.db')
                    cursor = conn.cursor()
                    cursor.execute("UPDATE historias_clinicas SET analisis_driver = ? WHERE id = ?", (texto_generado, paciente_id))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print("Error guardando en DB desde Ollama:", e)
                    
            return jsonify({"success": True, "respuesta": texto_generado})
        else:
            return jsonify({"success": False, "error": "Error del modelo Ollama: " + response.text}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    
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
@login_required
def submit_nutricion():
    if request.method == 'POST':
        p_id = session.get('paciente_id')
        if not p_id:
            return "Error: Sesión de paciente no válida.", 403

        # 2. Conectar a la base de datos
        conn = sqlite3.connect('prodi_salud.db')
        cursor = conn.cursor()
        
        try:
            # 3. Insertar/Actualizar datos de frecuencia en perfil_nutricional
            cursor.execute("SELECT id FROM perfil_nutricional WHERE paciente_id = ?", (p_id,))
            exists = cursor.fetchone()
            
            if exists:
                cursor.execute("""
                    UPDATE perfil_nutricional SET 
                        vegetariano = ?, consumo_leche_huevos = ?,
                        frecuencia_procesados = ?, frecuencia_frituras = ?, frecuencia_carnes_rojas = ?,
                        frecuencia_frutas_veg = ?, frecuencia_legumbres = ?, frecuencia_alcohol = ?,
                        frecuencia_bebidas_azucaradas = ?
                    WHERE paciente_id = ?
                """, (
                    request.form.get('vegetariano'),
                    request.form.get('consumo_leche_huevos'),
                    request.form.get('procesados'),
                    request.form.get('frituras'),
                    request.form.get('carnes_rojas'),
                    request.form.get('frutas_verduras'),
                    request.form.get('legumbres'),
                    request.form.get('alcohol'),
                    request.form.get('bebidas_azucaradas'),
                    p_id
                ))
            else:
                cursor.execute("""
                    INSERT INTO perfil_nutricional (
                        paciente_id, vegetariano, consumo_leche_huevos,
                        frecuencia_procesados, frecuencia_frituras, frecuencia_carnes_rojas,
                        frecuencia_frutas_veg, frecuencia_legumbres, frecuencia_alcohol,
                        frecuencia_bebidas_azucaradas
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p_id,
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

            # 4. Guardar Preferencias de Alimentos Individuales
            # Listas de IDs de alimentos por categoría
            frutas_ids = [
                'albaricoque', 'arandano', 'banana', 'cereza', 'frambuesa', 'fresa', 'granada', 'grosella', 
                'guayaba', 'higo', 'kiwan', 'kiwi', 'lima', 'litchi', 'mamon_chino', 'mandarina', 'mango', 
                'mangostan', 'manzana', 'maracuya', 'melocoton', 'melon', 'membrillo', 'mora', 'naranja', 
                'kumquat', 'nispero', 'papaya', 'pera', 'pina', 'pitahaya', 'pomelo', 'sandia', 
                'tamarindo_chino', 'tomate_arbol', 'uchuva', 'uva'
            ]
            
            vegetales_ids = [
                'acelga', 'alcachofa', 'apio', 'berenjena', 'berro', 'betabel', 'brocoli', 'alfalfa', 
                'calabaza', 'champinon', 'col', 'coliflor', 'esparrago', 'espinacas', 'guisantes', 
                'hinojo', 'lechuga', 'nabo', 'pepino', 'rabano', 'rucula', 'tomate', 'zanahoria', 'zucchini'
            ]

            proteinas_ids = [
                'atun_lata', 'atun_fresco', 'camarones', 'carne_molida', 'filet_bacalao', 'filet_res', 
                'filet_magra', 'filet_cochino', 'filet_jurel', 'filet_merluza', 'filet_pargo', 
                'filet_salmon', 'filet_trucha', 'higado_res', 'huevos', 'jamon', 'mortadela', 
                'muslo_pollo', 'pechuga_pollo', 'pescado_fresco', 'salchichas', 'sardina',
                'alubias', 'coles_bruselas', 'garbanzos', 'germen_trigo', 'lentejas', 'quinoa', 
                'semillas_calabaza', 'semillas_girasol', 'semillas_lino', 'sesamo', 'soja', 'tofu'
            ]

            carbo_ids = [
                'arepa', 'arroz_blanco', 'hojuelas_maiz', 'pan_blanco', 'pan_arabe', 'pan_frances', 
                'pan_hamburguesa', 'panqueca', 'pasta', 'tortilla',
                'arroz_integral', 'cebada', 'pan_integral', 'tortilla_integral', 'caraotas', 'papa', 
                'platano_verde', 'yuca', 'pasta_integral', 'platano_amarillo', 'arvejas_amarillas', 
                'arvejas_verdes', 'avena', 'cuscus', 'palomitas', 'maiz_grano'
            ]

            lacteos_ids = [
                'leche_completa', 'leche_descremada', 'queso_amarillo', 'queso_blanco', 
                'queso_mozarella', 'ricota', 'yogurt', 'yogurt_descremado'
            ]
            
            grasas_ids = [
                'aceite_ajonjoli', 'aceite_girasol', 'aceite_maiz', 'aceite_palma', 'aceite_soja', 
                'aceite_oliva', 'aceitunas', 'aguacate', 'almendras', 'cacahuete', 'crema_leche', 
                'mantequilla', 'margarina', 'mayonesa', 'merey', 'nueces', 'pistachos'
            ]
            
            # Guardar Frutas
            for food_id in frutas_ids:
                score = request.form.get(food_id)
                if score is not None:
                    cursor.execute("""
                        INSERT INTO preferencias_alimentos (paciente_id, alimento_id, tipo, puntuacion)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(paciente_id, alimento_id) DO UPDATE SET puntuacion = EXCLUDED.puntuacion, tipo = EXCLUDED.tipo
                    """, (p_id, food_id, 'fruta', int(score)))

            # Guardar Vegetales
            for food_id in vegetales_ids:
                score = request.form.get(food_id)
                if score is not None:
                    cursor.execute("""
                        INSERT INTO preferencias_alimentos (paciente_id, alimento_id, tipo, puntuacion)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(paciente_id, alimento_id) DO UPDATE SET puntuacion = EXCLUDED.puntuacion, tipo = EXCLUDED.tipo
                    """, (p_id, food_id, 'verdura', int(score)))

            # Guardar Proteínas
            for food_id in proteinas_ids:
                score = request.form.get(food_id)
                if score is not None:
                    # Corregido: tipo 'animal' y 'vegetal' para coincidir con reporte_nutricional
                    tipo_p = 'animal' if food_id in proteinas_ids[:22] else 'vegetal'
                    cursor.execute("""
                        INSERT INTO preferencias_alimentos (paciente_id, alimento_id, tipo, puntuacion)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(paciente_id, alimento_id) DO UPDATE SET puntuacion = EXCLUDED.puntuacion, tipo = EXCLUDED.tipo
                    """, (p_id, food_id, tipo_p, int(score)))
            
            # Guardar Carbohidratos
            for food_id in carbo_ids:
                score = request.form.get(food_id)
                if score is not None:
                    tipo_c = 'carbo_refinado' if food_id in carbo_ids[:10] else 'carbo_integral'
                    cursor.execute("""
                        INSERT INTO preferencias_alimentos (paciente_id, alimento_id, tipo, puntuacion)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(paciente_id, alimento_id) DO UPDATE SET puntuacion = EXCLUDED.puntuacion, tipo = EXCLUDED.tipo
                    """, (p_id, food_id, tipo_c, int(score)))

            # Guardar Lácteos
            for food_id in lacteos_ids:
                score = request.form.get(food_id)
                if score is not None:
                    cursor.execute("""
                        INSERT INTO preferencias_alimentos (paciente_id, alimento_id, tipo, puntuacion)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(paciente_id, alimento_id) DO UPDATE SET puntuacion = EXCLUDED.puntuacion, tipo = EXCLUDED.tipo
                    """, (p_id, food_id, 'lacteo', int(score)))

            # Guardar Grasas
            for food_id in grasas_ids:
                score = request.form.get(food_id)
                if score is not None:
                    cursor.execute("""
                        INSERT INTO preferencias_alimentos (paciente_id, alimento_id, tipo, puntuacion)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(paciente_id, alimento_id) DO UPDATE SET puntuacion = EXCLUDED.puntuacion, tipo = EXCLUDED.tipo
                    """, (p_id, food_id, 'grasa', int(score)))

            # Guardar Frecuencias de Comida Riesgosa
            risky_ids = [
                'hamburguesa', 'pizza', 'tequenos', 'empanadas', 'pollo_frito', 'papas_fritas', 
                'shawarma', 'hallaca', 'mondongo', 'pabellon', 'pasteles_fritos', 'patacon', 
                'hot_dog', 'helado', 'torta', 'donas', 'churros', 'refresco'
            ]
            freq_map = {'Nunca': 0, 'Mensualmente': 1, 'Semanalmente': 2, 'Diariamente': 3}
            
            for food_id in risky_ids:
                freq_val = request.form.get(food_id)
                if freq_val in freq_map:
                    cursor.execute("""
                        INSERT INTO preferencias_alimentos (paciente_id, alimento_id, tipo, puntuacion)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(paciente_id, alimento_id) DO UPDATE SET puntuacion = EXCLUDED.puntuacion, tipo = EXCLUDED.tipo
                    """, (p_id, food_id, 'frecuencia_riesgosa', freq_map[freq_val]))

            conn.commit()
            mensaje = "Perfil Nutricional y Preferencias guardados con éxito."
                
        except Exception as e:
            mensaje = f"Error en la base de datos: {e}"
        finally:
            conn.close()
            
        return redirect(url_for('landing_usuario', notification=mensaje))

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
        cursor.execute("PRAGMA table_info(seguimiento_twin)"); valid_cols = [r[1] for r in cursor.fetchall()]; filtered_data = {k: v for k, v in data.items() if k in valid_cols}; columnas = filtered_data.keys()
        placeholders = ", ".join(["?"] * len(columnas))
        query = f"INSERT INTO seguimiento_twin ({', '.join(columnas)}) VALUES ({placeholders})"
        
        cursor.execute(query, list(filtered_data.values()))
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "message": "Check-in guardado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/registrar_peso', methods=['POST'])
@login_required
def registrar_peso():
    """Ruta rápida para registrar el peso diario desde el landing"""
    data = request.get_json()
    p_id = session.get('paciente_id')
    peso = data.get('peso')
    
    if not p_id or peso is None:
        return jsonify({"error": "Datos incompletos"}), 400
        
    try:
        conn = sqlite3.connect('prodi_salud.db')
        cursor = conn.cursor()
        
        # Verificar si ya existe registro hoy
        cursor.execute("SELECT id FROM registro_peso WHERE paciente_id = ? AND fecha = date('now')", (p_id,))
        existente = cursor.fetchone()
        
        if existente:
            cursor.execute("UPDATE registro_peso SET peso = ? WHERE id = ?", (peso, existente[0]))
        else:
            cursor.execute("INSERT INTO registro_peso (paciente_id, fecha, peso) VALUES (?, date('now'), ?)", (p_id, peso))
            
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
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
        return render_template('index.html', pacientes=pacientes)
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
        data.get('pesimismo'), data.get('notas-medico'), ""
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
@login_required
def reporte_detalle(p_id):
    # Seguridad: Si el rol es paciente, solo puede ver SU reporte
    if session.get('role') == 'paciente' and session.get('paciente_id') != p_id:
        return redirect(url_for('landing_usuario'))

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

        return render_template('reporte_paciente.html', 
                               datos=paciente, 
                               inscripciones_nombres=lista_nombres,
                               role=session.get('role'))
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/get_submission/<int:p_id>')
@login_required
def get_submission(p_id):
    # Seguridad: Si el rol es paciente, solo puede pedir SUS datos JSON
    if session.get('role') == 'paciente' and session.get('paciente_id') != p_id:
        return jsonify({"error": "Acceso denegado"}), 403
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












@app.route('/base_de_datos')
def base_de_datos():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    try:
        conn = sqlite3.connect('prodi_salud.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Obtener nombres de columnas de Historias Clínicas (Excluyendo analisis_driver)
        cursor.execute("PRAGMA table_info(historias_clinicas)")
        cols_hc = [row[1] for row in cursor.fetchall() if row[1] != 'analisis_driver']
        
        # 2. Obtener nombres de columnas de Perfil Nutricional (Excluyendo IDs y fechas redundantes)
        cursor.execute("PRAGMA table_info(perfil_nutricional)")
        cols_pn = [row[1] for row in cursor.fetchall() if row[1] not in ['id', 'paciente_id', 'fecha_registro']]
        
        # 3. Query con JOIN aliasing para evitar colisiones de nombres (ej: frecuencia_alcohol)
        hc_select = ", ".join([f"hc.{c}" for c in cols_hc])
        pn_select = ", ".join([f"pn.{c} as pn_{c}" for c in cols_pn]) if cols_pn else ""
        
        # Crear lista de columnas finales para el header (usando los alias para PN)
        columnas_finales = cols_hc + [f"pn_{c}" for c in cols_pn]
        
        query = f"""
            SELECT {hc_select} {', ' + pn_select if pn_select else ''}
            FROM historias_clinicas hc
            LEFT JOIN perfil_nutricional pn ON hc.id = pn.paciente_id
            ORDER BY hc.id DESC
        """
        
        cursor.execute(query)
        filas_raw = cursor.fetchall()
        
        # 4. Obtener resumen de preferencias individuales para cada paciente
        filas = []
        for row in filas_raw:
            p_id = row['id']
            # Obtener top 3 frutas
            cursor.execute("""
                SELECT alimento_id FROM preferencias_alimentos 
                WHERE paciente_id = ? AND tipo = 'fruta' AND puntuacion >= 4
                LIMIT 3
            """, (p_id,))
            top_frutas = ", ".join([r[0].capitalize() for r in cursor.fetchall()])
            
            # Obtener top 3 verduras
            cursor.execute("""
                SELECT alimento_id FROM preferencias_alimentos 
                WHERE paciente_id = ? AND tipo = 'verdura' AND puntuacion >= 4
                LIMIT 3
            """, (p_id,))
            top_verduras = ", ".join([r[0].capitalize() for r in cursor.fetchall()])
            
            # Convertir row a dict y añadir extras
            d = dict(row)
            d['pn_top_frutas'] = top_frutas if top_frutas else "--"
            d['pn_top_verduras'] = top_verduras if top_verduras else "--"
            filas.append(d)
            
        columnas_finales = columnas_finales + ['pn_top_frutas', 'pn_top_verduras']
        
        conn.close()
        return render_template('base_de_datos.html', columnas=columnas_finales, filas=filas)
    except Exception as e:
        print(f"Error en base_de_datos extendida: {e}")
        return f"Error al cargar la base de datos extendida: {e}", 500


# --- 4. EJECUCIÓN DEL SERVIDOR (SIEMPRE AL FINAL) ---
if __name__ == '__main__':
    # Asegúrate de mantener tus rutas de /dashboard y /submit aquí arriba
    app.run(debug=True, port=5001)