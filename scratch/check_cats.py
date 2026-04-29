import pandas as pd
file_path = "/Volumes/SSD/Dropbox/Prodi/AI/PRODI AI System/Web Design/Registro Alimentos/Solo Macronutrientes Tabla Composicion De Alimentos Para Uso Práctico.xlsx"
df = pd.read_excel(file_path, header=None)
print("Rows 0-50 (Sample):")
pd.set_option('display.max_rows', 100)
print(df.iloc[:50, [0, 1]].to_string())
