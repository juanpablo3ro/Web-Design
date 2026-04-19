/**
 * PRODI Salud - Lógica del Cuestionario Nutricional
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Inicializar Sliders de Alimentos
    document.querySelectorAll('.food-preference input[type="range"]').forEach(function (slider) {
        // Función para actualizar el color y el valor del slider
        function updateSlider() {
            const value = slider.value;
            const sliderId = slider.id;
            const displaySpan = document.getElementById(sliderId + '-value');
            if (displaySpan) { displaySpan.textContent = value; }

            // Color dinámico para el slider (usando el color acento #0e647d)
            const percentage = (value - slider.min) / (slider.max - slider.min) * 100;
            slider.style.background = `linear-gradient(to right, #0e647d ${percentage}%, rgba(255,255,255,0.1) ${percentage}%)`;
        }

        // Evento de input
        slider.addEventListener('input', updateSlider);
        
        // Inicialización al cargar
        updateSlider();
    });

    // 2. Lógica de visibilidad para Vegetariano
    const vegetarianoSelect = document.getElementById('vegetariano');
    if (vegetarianoSelect) {
        // Función para validar visibilidad
        function checkVegetariano() {
            const container = document.getElementById('consumo_leche_huevos_container');
            if (container) {
                container.style.display = vegetarianoSelect.value === 'Sí' ? 'block' : 'none';
            }
        }

        vegetarianoSelect.addEventListener('change', checkVegetariano);
        
        // Inicialización al cargar
        checkVegetariano();
    }
});
