// Archivo: js_cuestionario.js

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
  return data; // Faltaba cerrar la función y retornar data
}

// --- INICIALIZACIÓN ---
document.addEventListener('DOMContentLoaded', () => {

  // 1. Inicializar Sliders (Frecuencia y Escalas)
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

  // 2. Lógica Condicional: Desea bajar de peso
  // Usamos el ID exacto que tienes en el HTML: "objetivo-extra"
  const radioBajarPeso = document.querySelectorAll('input[name="bajar-peso"]');
  const contenedorExtra = document.getElementById('objetivo-extra'); // <--- CAMBIO AQUÍ

  if (radioBajarPeso.length > 0 && contenedorExtra) {
    radioBajarPeso.forEach(radio => {
      radio.addEventListener('change', (e) => {
        console.log("Cambiando opción a:", e.target.value); // Para depuración

        if (e.target.value === "Sí") {
          contenedorExtra.style.display = 'block';
          // Hacer campos requeridos si se muestran
          contenedorExtra.querySelectorAll('input').forEach(el => el.required = true);
        } else {
          contenedorExtra.style.display = 'none';
          // Quitar requeridos si se ocultan y desmarcar radios ocultos para no enviar basura
          contenedorExtra.querySelectorAll('input').forEach(el => {
            el.required = false;
            el.checked = false;
          });
        }
      });
    });
  }

  // 3. Manejo del Envío del Formulario
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

      // Ocultar sección de peso tras reset
      if (contenedorExtra) contenedorExtra.style.display = 'none';

      // Resetear visualmente los valores de los sliders
      sliders.forEach(s => {
        const span = document.getElementById(s.id + '-value');
        if (span) span.textContent = s.value;
      });

    } catch (err) {
      alert('Error: ' + err.message);
    } finally {
      btnSubmit.disabled = false;
      btnSubmit.innerHTML = originalText;
    }
  });
});