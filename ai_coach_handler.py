import os
import json
import sqlite3
import requests
from datetime import datetime, date, timedelta

# Configuración de ruta y caché para recarga en caliente
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'ai_coach_config.json')
_config_cache = None
_config_mtime = 0

def get_config():
    """
    Carga y decodifica el archivo de configuración JSON.
    Detecta de forma dinámica si el archivo fue modificado y lo recarga en caliente (en tiempo real).
    """
    global _config_cache, _config_mtime
    try:
        if os.path.exists(CONFIG_PATH):
            current_mtime = os.path.getmtime(CONFIG_PATH)
            if _config_cache is None or current_mtime > _config_mtime:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    _config_cache = json.load(f)
                _config_mtime = current_mtime
                print(f"[AI Coach] Configuración recargada en caliente ({datetime.now()}). Modelo: {_config_cache.get('model_name')}")
        else:
            print(f"[AI Coach] Advertencia: No se encontró el archivo de configuración en {CONFIG_PATH}. Usando valores por defecto.")
            return get_default_config()
    except Exception as e:
        print(f"[AI Coach] Error al cargar la configuración: {e}. Usando valores por defecto.")
        if _config_cache is not None:
            return _config_cache
        return get_default_config()
    
    return _config_cache

def get_default_config():
    """Configuración por defecto en caso de error o archivo ausente."""
    return {
        "model_name": "gemma4:e4b",
        "ollama_url": "http://localhost:11434",
        "coach_system_prompt": "Eres el Coach Virtual de PRODI...",
        "dialogue_init_system_prompt_template": "Eres el Coach Virtual PRODI...",
        "dialogue_chat_system_prompt_template": "Eres el Coach Virtual PRODI...",
        "programa_info": "INFORMACIÓN DEL PROGRAMA PRODI..."
    }

def post_procesar_respuesta(text, context_type):
    """
    Capa de procesamiento en Python donde se puede interceptar y modificar
    la respuesta generada por Ollama antes de retornarla o guardarla en DB.
    
    Parámetros:
    - text (str): El texto generado por el modelo de IA.
    - context_type (str): El contexto de la llamada ('coach_narrative' o 'coach_dialogue').
    
    Retorna:
    - str: El texto final modificado.
    """
    # =========================================================================
    # CAPA DE MODIFICACIÓN DE LA RESPUESTA (Aquí puedes agregar tu lógica)
    # =========================================================================
    
    # Ejemplo 1: Reemplazar palabras o corregir formato
    # text = text.replace("algun_termino", "otro_termino")
    
    # Ejemplo 2: Modificar respuestas según el contexto
    # if context_type == 'coach_narrative':
    #     text = text + "\n\n---\n*Nota: Este análisis fue generado por el Coach Virtual y validado por la capa de Python.*"
        
    return text


def generar_coach_narrativa_impl(texto_paciente, paciente_id):
    """
    Implementación del análisis narrativo de datos del paciente utilizando Ollama.
    """
    config = get_config()
    model_name = config.get("model_name", "gemma4:e4b")
    ollama_url = config.get("ollama_url", "http://localhost:11434")
    system_prompt = config.get("coach_system_prompt", "")
    
    try:
        # Petición a la API de Ollama usando el endpoint /api/generate
        # Pasamos el Prompt del Sistema en el parámetro "system" para que se aplique en tiempo real
        payload = {
            "model": model_name,
            "prompt": texto_paciente,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.5
            }
        }
        
        response = requests.post(f"{ollama_url}/api/generate", json=payload, timeout=240)
        
        if response.ok:
            result = response.json()
            texto_generado = result.get('response', '')
            
            # Aplicar la capa de post-procesamiento en Python
            texto_final = post_procesar_respuesta(texto_generado, 'coach_narrative')
            
            # Guardado directo en la base de datos
            if paciente_id:
                try:
                    conn = sqlite3.connect('prodi_salud.db')
                    cursor = conn.cursor()
                    cursor.execute("UPDATE historias_clinicas SET analisis_driver = ? WHERE id = ?", (texto_final, paciente_id))
                    conn.commit()
                    conn.close()
                except Exception as db_err:
                    print("[AI Coach] Error guardando en DB:", db_err)
                    
            return {"success": True, "respuesta": texto_final}
        else:
            return {"success": False, "error": f"Error del modelo Ollama ({response.status_code}): {response.text}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


def dialogo_coach_impl(p_id, user_message, is_init):
    """
    Implementación del diálogo del avatar coach.
    Calcula las métricas actuales del paciente, recopila el historial y llama a Ollama.
    """
    try:
        conn = sqlite3.connect('prodi_salud.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Obtener datos del paciente
        cursor.execute("SELECT * FROM historias_clinicas WHERE id = ?", (p_id,))
        paciente = cursor.fetchone()
        if not paciente:
            conn.close()
            return {"success": False, "error": "Paciente no encontrado en base de datos"}
            
        # 2. Calcular métricas actuales (Días, racha, adherencia, pendientes)
        try:
            fecha_str = paciente['fecha_registro']
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
        semana_actual = (dias_programa // 7) + 1
        
        # Adherencia y racha
        cursor.execute("SELECT AVG(porcentaje_visto) FROM progreso_video WHERE paciente_id = ?", (p_id,))
        avg_edu_val = cursor.fetchone()
        avg_edu = avg_edu_val[0] if avg_edu_val and avg_edu_val[0] is not None else 0
        edu_score = (avg_edu / 100) * 40
        
        cursor.execute("SELECT COUNT(DISTINCT fecha) FROM diario_alimentos WHERE paciente_id = ? AND fecha >= date('now', '-7 days')", (p_id,))
        cant_nut = cursor.fetchone()[0] or 0
        nut_score = (min(cant_nut, 7) / 7) * 30
        
        cursor.execute("SELECT COUNT(DISTINCT fecha) FROM registro_peso WHERE paciente_id = ? AND fecha >= date('now', '-7 days')", (p_id,))
        cant_peso = cursor.fetchone()[0] or 0
        peso_score = (min(cant_peso, 7) / 7) * 20
        
        cursor.execute("SELECT COUNT(DISTINCT fecha) FROM registro_actividad WHERE paciente_id = ? AND fecha >= date('now', '-7 days')", (p_id,))
        cant_act = cursor.fetchone()[0] or 0
        act_score = (min(cant_act, 7) / 7) * 10
        
        adherencia_total = round(edu_score + nut_score + peso_score + act_score)
        
        # Racha
        cursor.execute("SELECT DISTINCT fecha FROM diario_alimentos WHERE paciente_id = ? ORDER BY fecha DESC LIMIT 15", (p_id,))
        fechas_reg = [r['fecha'] for r in cursor.fetchall() if r['fecha']]
        streak = 0
        if fechas_reg:
            hoy = date.today()
            current_check = hoy
            for f_str in fechas_reg:
                try:
                    f_date = datetime.strptime(str(f_str).split(' ')[0], '%Y-%m-%d').date()
                    if f_date == current_check or f_date == current_check - timedelta(days=1):
                        streak += 1
                        current_check = f_date
                    else: 
                        break
                except Exception: 
                    continue

        # Tareas Pendientes (Misiones Diarias y Globales)
        pendientes = []
        
        # Misiones de configuración inicial
        if not paciente['reporte_visto']:
            pendientes.append("Revisar su Reporte de Salud Inicial (Análisis y Diagnóstico)")
        
        cursor.execute("SELECT id FROM perfil_nutricional WHERE paciente_id = ?", (p_id,))
        if not cursor.fetchone():
            pendientes.append("Completar el Cuestionario Nutricional para generar su plan de alimentación")
            
        # Misiones Diarias Clave (Hacer contenido, peso, alimentación, actividad)
        # 1. Contenido del nodo (video/sesión)
        cursor.execute("SELECT id FROM progreso_video WHERE paciente_id = ? AND video_id = ? AND porcentaje_visto >= 90", (p_id, semana_actual))
        if not cursor.fetchone():
            pendientes.append(f"Ver el contenido del nodo de hoy (Sesión {semana_actual})")
            
        # 2. Registro de Peso
        cursor.execute("SELECT peso FROM registro_peso WHERE paciente_id = ? AND fecha = date('now')", (p_id,))
        if not cursor.fetchone():
            pendientes.append("Registrar su peso de hoy")
            
        # 3. Registro de Alimentación
        cursor.execute("SELECT id FROM diario_alimentos WHERE paciente_id = ? AND fecha >= date('now')", (p_id,))
        if not cursor.fetchone():
            pendientes.append("Registrar sus comidas de hoy en el diario")
            
        # 4. Registro de Actividad Física
        cursor.execute("SELECT id FROM registro_actividad WHERE paciente_id = ? AND fecha >= date('now')", (p_id,))
        if not cursor.fetchone():
            pendientes.append("Registrar su actividad física / pasos de hoy")
            
        pendientes_texto = ", ".join(pendientes) if pendientes else "¡Al día con todas las misiones de hoy!"
        
        # 3. Guardar mensaje del usuario si existe
        if user_message:
            cursor.execute("INSERT INTO mensajes_coach (paciente_id, sender, mensaje, is_init) VALUES (?, 'user', ?, 0)", (p_id, user_message))
            conn.commit()
            
        # 4. Obtener historial reciente de conversación (últimos 6 mensajes)
        cursor.execute("SELECT sender, mensaje FROM mensajes_coach WHERE paciente_id = ? ORDER BY fecha DESC LIMIT 6", (p_id,))
        historial_rows = cursor.fetchall()[::-1] # Invertir para orden cronológico
        
        historial_texto = ""
        for r in historial_rows:
            rol = "Participante" if r['sender'] == 'user' else "Coach"
            historial_texto += f"{rol}: {r['mensaje']}\n"
            
        conn.close()
        
        # 5. Cargar configuración y formatear plantillas de prompts
        config = get_config()
        model_name = config.get("model_name", "gemma4:e4b")
        ollama_url = config.get("ollama_url", "http://localhost:11434")
        
        paciente_nombre = paciente['nombre'] if paciente['nombre'] else "Participante"
        
        if is_init:
            template = config.get("dialogue_init_system_prompt_template", "")
            prompt_instrucciones = template.format(
                paciente_nombre=paciente_nombre,
                dias_programa=dias_programa,
                semana_actual=semana_actual,
                pendientes_texto=pendientes_texto
            )
            # Para la bienvenida, no hay un prompt de usuario propiamente, iniciamos la conversación
            prompt_usuario = "Hola Coach, acabo de iniciar sesión en el portal. Preséntate y guíame con mis tareas pendientes de hoy."
        else:
            template = config.get("dialogue_chat_system_prompt_template", "")
            prompt_instrucciones = template.format(
                paciente_nombre=paciente_nombre,
                dias_programa=dias_programa,
                semana_actual=semana_actual,
                historial_texto=historial_texto
            )
            prompt_usuario = f"Pregunta del participante: {user_message}"
            
        # Unimos las instrucciones de la sesión con la información general del programa
        system_prompt = f"{prompt_instrucciones}\n\n{config.get('programa_info', '')}"
        
        # Llamada a Ollama con system prompt y user prompt
        payload = {
            "model": model_name,
            "prompt": prompt_usuario,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.7
            }
        }
        
        response = requests.post(f"{ollama_url}/api/generate", json=payload, timeout=360)
        
        if response.ok:
            result = response.json()
            texto_generado = result.get('response', '').strip()
            
            # Aplicar post-procesamiento
            texto_final = post_procesar_respuesta(texto_generado, 'coach_dialogue')
            
            # Guardar respuesta del coach en la base de datos
            conn = sqlite3.connect('prodi_salud.db')
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO mensajes_coach (paciente_id, sender, mensaje, is_init) VALUES (?, 'coach', ?, ?)", 
                (p_id, texto_final, 1 if is_init else 0)
            )
            conn.commit()
            conn.close()
            
            return {"success": True, "respuesta": texto_final}
        else:
            return {"success": False, "error": f"Error de Ollama ({response.status_code}): {response.text}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}
