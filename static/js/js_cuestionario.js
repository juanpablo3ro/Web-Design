// Archivo: js_cuestionario.js
// Serializa el formulario completo, calcula índices de salud y envía JSON a /submit_form

/**
 * Función para convertir valor de respuesta a número (0-3)
 * Para nada = 0, Algunos días = 1, Más de la mitad = 2, Casi todos = 3
 */
function responseToScore(response) {
  const scoreMap = {
    'Para nada': 0,
    'Algunos días': 1,
    'Más de la mitad de los días': 2,
    'Casi todos los días': 3
  };
  return scoreMap[response] || 0;
}

/**
 * Función para mostrar/ocultar el campo de objetivo extra preguntas obesidad
 */
document.querySelectorAll('input[name="bajar-peso"]').forEach(el => {
  el.addEventListener('change', function () {
    const extra = document.getElementById('objetivo-extra');
    if (this.value === "Sí") {
      extra.style.display = "block";
    } else {
      extra.style.display = "none";
    }
  });
});


/**
 * Calcula el Índice de Masa Corporal (IMC)
 * IMC = peso (kg) / (talla (m))²
 * talla debe estar en centímetros
 */
function calculateIMC(peso, talla) {
  if (!peso || !talla || peso <= 0 || talla <= 0) return null;
  const tallaMts = talla / 100;
  return (peso / (tallaMts * tallaMts)).toFixed(1);
}

/**
 * Determina el estado nutricional basado en IMC
 * Bajo peso: < 18.5
 * Normopeso: 18.5 - 24.9
 * Sobrepeso: 25.0 - 29.9
 * Obesidad: >= 30
 */
function getEstadoNutricional(imc) {
  if (!imc) return null;
  const imcNum = parseFloat(imc);
  if (imcNum < 18.5) return 'Bajo peso';
  if (imcNum < 25) return 'Normopeso';
  if (imcNum < 30) return 'Sobrepeso';
  return 'Obesidad';
}

/**
 * Determina si hay obesidad abdominal
 * Presente: mujer y circunferencia >= 86 cm O hombre >= 90 cm
 */
function getObesidadAbdominal(perimetroAbdominal, sexo) {
  if (!perimetroAbdominal || !sexo) return null;
  const perimetro = parseFloat(perimetroAbdominal);
  if (sexo === 'Femenino') {
    return perimetro >= 86 ? 'Presente' : 'Normal';
  } else if (sexo === 'Masculino') {
    return perimetro >= 90 ? 'Presente' : 'Normal';
  }
  return null;
}

/**
 * Evalúa la calidad del sueño
 * < 1 = Terrible
 * < 4 = Mala
 * < 7 = Regular
 * < 10 = Buena
 * = 10 = Excelente
 */
function getCalidadSueno(puntaje) {
  if (puntaje === null || puntaje === undefined || puntaje === '') return null;
  const p = parseFloat(puntaje);
  if (p < 1) return 'Terrible';
  if (p < 4) return 'Mala';
  if (p < 7) return 'Regular';
  if (p < 10) return 'Buena';
  if (p === 10) return 'Excelente';
  return null;
}

/**
 * Calcula puntaje de ansiedad (preguntas 37 + 38)
 * Suma de dos respuestas (0-3 cada una)
 * Presente >= 3, resto Ausente
 */
function calcularAnsiedad(ansioso, preocupacion) {
  const score1 = responseToScore(ansioso);
  const score2 = responseToScore(preocupacion);
  const total = score1 + score2;
  return {
    puntaje: total,
    estado: total >= 3 ? 'Presente' : 'Ausente'
  };
}

/**
 * Calcula puntaje de depresión (preguntas 39 + 40)
 * Suma de dos respuestas (0-3 cada una)
 * Presente >= 3, resto Ausente
 */
function calcularDepresion(interes, deprimido) {
  const score1 = responseToScore(interes);
  const score2 = responseToScore(deprimido);
  const total = score1 + score2;
  return {
    puntaje: total,
    estado: total >= 3 ? 'Presente' : 'Ausente'
  };
}

/**
 * Evalúa riesgo de apnea obstructiva del sueño
 * Presente si: ronca (pregunta 33) = Sí AND circunferencia cuello >= 40 cm
 */
function riesgoApneaSueno(ronca, circunferenciaCuello) {
  if (!ronca || !circunferenciaCuello) return null;
  const cuello = parseFloat(circunferenciaCuello);
  if (ronca === 'Sí' && cuello >= 40) {
    return 'Presente';
  }
  return 'Ausente';
}

function serializeForm(form) {
  const data = {};
  const elements = Array.from(form.elements).filter(el => el.name && !el.disabled);

  elements.forEach(el => {
    const name = el.name;
    const type = el.type;

    if (type === 'checkbox') {
      if (!data[name]) data[name] = [];
      if (el.checked) data[name].push(el.value);
    } else if (type === 'radio') {
      if (el.checked) data[name] = el.value;
    } else if (el.tagName === 'SELECT' && el.multiple) {
      data[name] = Array.from(el.selectedOptions).map(o => o.value);
    } else {
      // Inputs normales, textarea, selects single
      data[name] = el.value;
    }
  });

  // Añadir timestamp
  data.timestamp = new Date().toISOString();

  // CALCULAR ÍNDICES DE SALUD
  const calculosde_Salud = {};

  // 1. IMC
  const imc = calculateIMC(data.peso, data.talla);
  if (imc) {
    calculosde_Salud.imc = parseFloat(imc);
    calculosde_Salud.estado_nutricional = getEstadoNutricional(imc);
  }

  // 2. Obesidad abdominal
  const obesidadAbdominal = getObesidadAbdominal(data['perimetro-abdominal'], data.sexo);
  if (obesidadAbdominal) {
    calculosde_Salud.obesidad_abdominal = obesidadAbdominal;
  }

  // 3. Calidad del sueño
  const calidadSueno = getCalidadSueno(data['calidad-sueno']);
  if (calidadSueno) {
    calculosde_Salud.calidad_sueno_evaluacion = calidadSueno;
  }

  // 4. Síntomas de ansiedad
  const ansiedad = calcularAnsiedad(data.ansioso, data.preocupacion);
  if (ansiedad) {
    calculosde_Salud.puntaje_ansiedad = ansiedad.puntaje;
    calculosde_Salud.sintomas_ansiedad = ansiedad.estado;
  }

  // 5. Síntomas de depresión
  const depresion = calcularDepresion(data.interes, data.deprimido);
  if (depresion) {
    calculosde_Salud.puntaje_depresion = depresion.puntaje;
    calculosde_Salud.sintomas_depresion = depresion.estado;
  }

  // 6. Riesgo de apnea obstructiva del sueño
  const apnea = riesgoApneaSueno(data.ronca, data['circunferencia-cuello']);
  if (apnea) {
    calculosde_Salud.riesgo_apnea_sueno = apnea;
  }

  // Agregar cálculos al objeto de datos
  data.calculos_salud = calculosde_Salud;

  return data;
}

function showMessage(text, isError = false) {
  const box = document.getElementById('message-box');
  if (!box) return alert(text);
  box.className = isError ? 'message error' : 'message success';
  box.textContent = text;
  box.classList.remove('hidden');
  setTimeout(() => box.classList.add('hidden'), 6000);
}

document.addEventListener('DOMContentLoaded', () => {
  // Inicializar sliders: actualizar el span con id '<slider-id>-value' al mover el control
  const sliders = document.querySelectorAll('.modern-range');
  sliders.forEach(slider => {
    const valueSpan = document.getElementById(slider.id + '-value');
    if (!valueSpan) return;
    // establecer valor inicial
    valueSpan.textContent = slider.value;
    slider.addEventListener('input', () => {
      valueSpan.textContent = slider.value;
    });
  });

  const form = document.getElementById('health-form') || document.getElementById('questionnaire-form');
  if (!form) return console.warn('Formulario no encontrado: id=health-form o questionnaire-form');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = serializeForm(form);

    try {
      const res = await fetch('/submit_form', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || 'Error en el servidor');
      }

      const json = await res.json();
      showMessage('Formulario enviado. ID: ' + (json.id || '---'));
      form.reset();
    } catch (err) {
      console.error(err);
      showMessage('Error enviando formulario: ' + err.message, true);
    }
  });
});