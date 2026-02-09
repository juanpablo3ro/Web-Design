import sqlite3

def crear_tabla_nutricion():
    conn = sqlite3.connect('prodi_salud.db')
    cursor = conn.cursor()
    
    # Aquí pegamos el código SQL que te di
    sql_command = """
    CREATE TABLE IF NOT EXISTS perfil_nutricional (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER,
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
    );
    """
    
    cursor.execute(sql_command)
    conn.commit()
    conn.close()
    print("¡Tabla creada con éxito!")

if __name__ == "__main__":
    crear_tabla_nutricion()