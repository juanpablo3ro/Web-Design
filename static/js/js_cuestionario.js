// Archivo: js_cuestionario.js

// --- FUNCIONES DE APOYO ---
function responseToScore(response) {
  const scoreMap = {
    'Para nada': 0,
    'Algunos días': 1,
    'Más de la mitad de los días': 2,
    'Casi todos los días': 3
  };
  return scoreMap[response] || 0;
}

// Lógica para mostrar/ocultar objetivo extra
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

function calculateIMC(peso, talla) {
  if (!peso || !talla || peso <= 0 || talla <= 0) return null;
  const tallaMts = talla / 100;
  return (peso / (tallaMts * tallaMts)).toFixed(1);
}

function getEstadoNutricional(imc) {
  if (!imc) return null;
  const imcNum = parseFloat(imc);
  if (imcNum < 18.5) return 'Bajo peso';
  if (imcNum < 25) return 'Normopeso';
  if (imcNum < 30) return 'Sobrepeso';
  return 'Obesidad';
}

function getObesidadAbdominal(perimetroAbdominal, sexo) {
  if (!perimetroAbdominal || !sexo) return null;
  const perimetro = parseFloat(perimetroAbdominal);
  if (sexo === 'Femenino') return perimetro >= 86 ? 'Presente' : 'Normal';
  if (sexo === 'Masculino') return perimetro >= 90 ? 'Presente' : 'Normal';
  return null;
}

function getCalidadSueno(puntaje) {
  if (puntaje === null || puntaje === undefined || puntaje === '') return null;
  const p = parseFloat(puntaje);
  if (p < 1) return 'Terrible';
  if (p < 4) return 'Mala';
  if (p < 7) return 'Regular';
  if (p < 10) return 'Buena';
  if (p == 10) return 'Excelente';
  return null;
}

function calcularAnsiedad(ansioso, preocupacion) {
  const s1 = responseToScore(ansioso);
  const s2 = responseToScore(preocupacion);
  const total = s1 + s2;
  return { puntaje: total, estado: total >= 3 ? 'Presente' : 'Ausente' };
}

function calcularDepresion(interes, deprimido) {
  const s1 = responseToScore(interes);
  const s2 = responseToScore(deprimido);
  const total = s1 + s2;
  return { puntaje: total, estado: total >= 3 ? 'Presente' : 'Ausente' };
}

function riesgoApneaSueno(ronca, circunferenciaCuello) {
  if (!ronca || !circunferenciaCuello) return null;
  const cuello = parseFloat(circunferenciaCuello);
  return (ronca === 'Sí' && cuello >= 40) ? 'Presente' : 'Ausente';
}

function serializeForm(form) {
  const data = {};
  const elements = Array.from(form.elements).filter(el => el.name && !el.disabled);

  elements.forEach(el => {
    if (el.type === 'checkbox') {
      if (!data[el.name]) data[el.name] = [];
      if (el.checked) data[el.name].push(el.value);
    } else if (el.type === 'radio') {
      if (el.checked) data[el.name] = el.value;
    } else {
      data[el.name] = el.value;
    }
  });

  // Cálculos de Salud Automáticos
  const cal = {};
  const imc = calculateIMC(data.peso, data.talla);
  if (imc) { cal.imc = imc; cal.estado_nutricional = getEstadoNutricional(imc); }
  cal.obesidad_abdominal = getObesidadAbdominal(data['perimetro-abdominal'], data.sexo);
  cal.calidad_sueno_evaluacion = getCalidadSueno(data['calidad-sueno']);
  
  const ans = calcularAnsiedad(data.ansioso, data.preocupacion);
  cal.sintomas_ansiedad = ans.estado;
  
  const dep = calcularDepresion(data.interes, data.deprimido);
  cal.sintomas_depresion = dep.estado;
  
  data.calculos_salud = cal;
  return data;
}

// --- INICIALIZACIÓN ---
document.addEventListener('DOMContentLoaded', () => {
  // 1. Inicializar Sliders (Esto es lo que faltaba en tu versión)
  const sliders = document.querySelectorAll('.modern-range');
  sliders.forEach(slider => {
    const valueSpan = document.getElementById(slider.id + '-value');
    if (valueSpan) {
      valueSpan.textContent = slider.value;
      slider.addEventListener('input', () => {
        valueSpan.textContent = slider.value;
      });
    }
  });

  // 2. Manejo del Formulario
  const form = document.getElementById('health-form') || document.getElementById('questionnaire-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const btnSubmit = form.querySelector('button[type="submit"]');
    const originalText = btnSubmit.innerHTML;
    
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = 'Enviando información segura...';

    const data = serializeForm(form);

    try {
      const res = await fetch('/submit_form', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });

      if (!res.ok) throw new Error('Error en el servidor');

      alert("¡Registro Exitoso!\n\nGracias por completar el cuestionario. Tu reporte será enviado pronto.");
      
      form.reset();
      // Resetear visualmente los valores de los sliders tras el reset
      sliders.forEach(s => {
          const span = document.getElementById(s.id + '-value');
          if(span) span.textContent = s.value;
      });

    } catch (err) {
      alert('Error: ' + err.message);
    } finally {
      // Restaurar botón siempre (éxito o error)
      btnSubmit.disabled = false;
      btnSubmit.innerHTML = originalText;
    }
  });
});