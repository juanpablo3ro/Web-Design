import sqlite3

def check_nulls():
    conn = sqlite3.connect('prodi_salud.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM historias_clinicas ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    
    if not row:
        print("No hay pacientes.")
        return
        
    print(f"Checking nulls for {row['nombre']} {row['apellidos']} (ID: {row['id']})")
    
    d = dict(row)
    null_cols = [k for k, v in d.items() if v is None or v == '']
    print(f"Columnas con valor nulo o vacío ({len(null_cols)}):")
    for c in null_cols:
        print(f"  {c}")
        
    conn.close()

if __name__ == "__main__":
    check_nulls()
