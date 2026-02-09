document.addEventListener('DOMContentLoaded', function () {
    if (rawData.length === 0) {
        console.log("No hay datos históricos para este paciente.");
        return;
    }

    // 1. Preparar datos
    // Invertimos el array para que la línea de tiempo vaya de pasado a presente (izquierda a derecha)
    const history = [...rawData].reverse();
    const labels = history.map(h => h.fecha_checkin.split(' ')[0]);
    const weights = history.map(h => h.peso);
    const steps = history.map(h => h.pasos_dia);

    // Actualizar peso actual en el card principal
    const currentWeightElement = document.getElementById('current-weight');
    if (currentWeightElement) {
        currentWeightElement.innerText = weights[weights.length - 1] + " kg";
    }

    // Configuración global de fuentes para Chart.js (Blanco para que se vea en el fondo oscuro)
    Chart.defaults.color = '#ffffff';
    Chart.defaults.font.family = 'Georgia, serif';

    // 2. Gráfico de Peso (Usando el NARANJA ACCENT del reporte)
    const ctxWeight = document.getElementById('weightChart').getContext('2d');
    new Chart(ctxWeight, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Peso Corporal (kg)',
                data: weights,
                borderColor: '#F27405', // Naranja exacto de tu CSS
                backgroundColor: 'rgba(242, 116, 5, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 5,
                pointBackgroundColor: '#F27405'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { labels: { font: { size: 14 } } }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    grid: { color: 'rgba(255,255,255,0.05)' }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });

    // 3. Gráfico de Pasos (Usando el TURQUESA PRIMARY del reporte)
    const ctxSteps = document.getElementById('stepsChart').getContext('2d');
    new Chart(ctxSteps, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Pasos Diarios',
                data: steps,
                backgroundColor: '#02735E', // Turquesa exacto de tu CSS
                borderRadius: 5
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { labels: { font: { size: 14 } } }
            },
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    });
});

// Lógica para el botón de Gemini (Análisis de Evolución)
document.getElementById('btn-analyze-dt').addEventListener('click', function () {
    const btn = this;
    btn.innerText = "Analizando datos con IA...";
    btn.style.opacity = "0.6";

    // Aquí es donde en el siguiente paso haremos el fetch a Flask
    setTimeout(() => {
        alert("Simulación: Gemini está analizando que tu peso bajó de " + rawData[rawData.length - 1].peso + "kg a " + rawData[0].peso + "kg.");
        btn.innerText = "Generar Análisis de Evolución (Gemini)";
        btn.style.opacity = "1";
    }, 2000);
});