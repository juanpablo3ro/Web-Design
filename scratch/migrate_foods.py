import pandas as pd
import sqlite3
import os

file_path = "/Volumes/SSD/Dropbox/Prodi/AI/PRODI AI System/Web Design/Registro Alimentos/Solo Macronutrientes Tabla Composicion De Alimentos Para Uso Práctico.xlsx"
db_path = "/Volumes/SSD/Dropbox/Prodi/AI/PRODI AI System/Web Design/prodi_salud.db"

def migrate():
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    df = pd.read_excel(file_path, header=None)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create the table
    cursor.execute("DROP TABLE IF EXISTS alimentos_master")
    cursor.execute('''
        CREATE TABLE alimentos_master (
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
    
    current_category = "General"
    count = 0
    
    for index, row in df.iterrows():
        # Skip header rows (first 4-5 rows)
        if index < 4:
            continue
            
        col0 = row[0]
        col1 = row[1]
        
        # Check if it's a category
        if pd.isna(col0) and isinstance(col1, str) and len(col1.strip()) > 0:
            if "TABLA" not in col1 and "Codigo" not in col1:
                current_category = col1.strip()
                # print(f"Category: {current_category}")
                continue
        
        # Check if it's a food item (has a code)
        if not pd.isna(col0) and (isinstance(col0, (int, float, str))):
            try:
                codigo = str(col0)
                nombre = str(col1).strip()
                porcion = float(row[2]) if not pd.isna(row[2]) else 100.0
                energia = float(row[3]) if not pd.isna(row[3]) else 0.0
                proteina = float(row[5]) if not pd.isna(row[5]) else 0.0
                grasa = float(row[8]) if not pd.isna(row[8]) else 0.0
                carbos = float(row[9]) if not pd.isna(row[9]) else 0.0
                fibra = float(row[11]) if not pd.isna(row[11]) else 0.0
                
                cursor.execute('''
                    INSERT INTO alimentos_master 
                    (codigo, nombre, categoria, porcion_g, energia_kcal, proteina_g, grasa_g, carbohidratos_g, fibra_g)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (codigo, nombre, current_category, porcion, energia, proteina, grasa, carbos, fibra))
                count += 1
            except (ValueError, IndexError) as e:
                # print(f"Error in row {index}: {e}")
                continue
                
    conn.commit()
    conn.close()
    print(f"Successfully migrated {count} food items.")

if __name__ == "__main__":
    migrate()
