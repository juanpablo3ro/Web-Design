import sqlite3

def test_query():
    conn = sqlite3.connect('prodi_salud.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Historias Clínicas cols
    cursor.execute("PRAGMA table_info(historias_clinicas)")
    cols_hc = [row[1] for row in cursor.fetchall() if row[1] != 'analisis_driver']
    
    # Perfil Nutricional cols
    cursor.execute("PRAGMA table_info(perfil_nutricional)")
    cols_pn = [row[1] for row in cursor.fetchall() if row[1] not in ['id', 'paciente_id', 'fecha_registro']]
    
    # Join
    hc_select = ", ".join([f"hc.{c}" for c in cols_hc])
    pn_select = ", ".join([f"pn.{c} as pn_{c}" for c in cols_pn]) # Aliasing to avoid collisions
    
    query = f"""
        SELECT {hc_select}, {pn_select}
        FROM historias_clinicas hc
        LEFT JOIN perfil_nutricional pn ON hc.id = pn.paciente_id
        ORDER BY hc.id DESC
    """
    
    cursor.execute(query)
    filas = cursor.fetchall()
    
    print(f"Total filas: {len(filas)}")
    if filas:
        f = dict(filas[0])
        print("Columnas en el resultado:")
        print(f.keys())
        print("\nEjemplo de datos nutricionales:")
        print(f"Vegetariano: {f.get('pn_vegetariano')}")
        print(f"Frecuencia Alcohol (PN): {f.get('pn_frecuencia_alcohol')}")
        
    conn.close()

if __name__ == "__main__":
    test_query()
