import sqlite3

def check_prefs():
    conn = sqlite3.connect('prodi_salud.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get latest patient
    cursor.execute("SELECT id, nombre, apellidos FROM historias_clinicas ORDER BY id DESC LIMIT 1")
    patient = cursor.fetchone()
    
    if not patient:
        print("No hay pacientes.")
        return
        
    p_id = patient['id']
    print(f"Checking preferences for {patient['nombre']} {patient['apellidos']} (ID: {p_id})")
    
    cursor.execute("SELECT * FROM preferencias_alimentos WHERE paciente_id = ?", (p_id,))
    prefs = cursor.fetchall()
    
    print(f"Total preferencias: {len(prefs)}")
    if prefs:
        print("Primeras 10 preferencias:")
        for p in prefs[:10]:
            print(f"  {p['alimento_id']} ({p['tipo']}): {p['puntuacion']}")
            
        # Check for the protein bug
        cursor.execute("SELECT * FROM preferencias_alimentos WHERE paciente_id = ? AND tipo IN ('proteina_animal', 'proteina_vegetal', 'animal', 'vegetal')", (p_id,))
        p_prefs = cursor.fetchall()
        print("\nProteínas encontradas:")
        for p in p_prefs:
            print(f"  {p['alimento_id']} ({p['tipo']}): {p['puntuacion']}")

        # Check for risky foods
        cursor.execute("SELECT * FROM preferencias_alimentos WHERE paciente_id = ? AND tipo = 'frecuencia_riesgosa'", (p_id,))
        r_prefs = cursor.fetchall()
        print("\nComidas Riesgosas encontradas:")
        for p in r_prefs:
            print(f"  {p['alimento_id']} ({p['tipo']}): {p['puntuacion']}")
            
    conn.close()

if __name__ == "__main__":
    check_prefs()
