import requests
import sqlite3

# This test requires the server to be running. 
# Alternatively, we can test the database logic directly.

def test_db_logic():
    # Simulate a submission to submit_nutricion
    p_id = 4 # Use the test patient ID
    
    # Mock data
    mock_form = {
        'vegetariano': 'No',
        'procesados': 'Semanalmente',
        'hamburguesa': 'Mensualmente',
        'albaricoque': '5',
        'atun_fresco': '4',
        'arroz_blanco': '3',
        'leche_entera': '2',
        'aceite_oliva': '1'
    }
    
    conn = sqlite3.connect('prodi_salud.db')
    cursor = conn.cursor()
    
    # Simulate the protein save fix
    proteinas_ids = ['atun_fresco'] # simplified
    score = mock_form.get('atun_fresco')
    tipo_p = 'animal' # The fix I applied
    
    cursor.execute("""
        INSERT INTO preferencias_alimentos (paciente_id, alimento_id, tipo, puntuacion)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(paciente_id, alimento_id) DO UPDATE SET puntuacion = EXCLUDED.puntuacion, tipo = EXCLUDED.tipo
    """, (p_id, 'atun_fresco', tipo_p, int(score)))
    
    conn.commit()
    
    # Verify
    cursor.execute("SELECT tipo FROM preferencias_alimentos WHERE paciente_id = ? AND alimento_id = ?", (p_id, 'atun_fresco'))
    res = cursor.fetchone()
    print(f"Tipo guardado para atun_fresco: {res[0]}")
    
    conn.close()

if __name__ == "__main__":
    test_db_logic()
