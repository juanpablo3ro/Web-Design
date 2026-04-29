import pandas as pd
import os

file_path = "/Volumes/SSD/Dropbox/Prodi/AI/PRODI AI System/Web Design/Registro Alimentos/Solo Macronutrientes Tabla Composicion De Alimentos Para Uso Práctico.xlsx"

try:
    # Reading without header first to see where the data starts
    df = pd.read_excel(file_path, header=None)
    print("Shape:", df.shape)
    print("\nFirst 15 rows (all columns):")
    # Set display options to see all columns
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print(df.head(15).to_string())
except Exception as e:
    print(f"Error reading file: {e}")
