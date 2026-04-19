/**
 * PRODI Salud - Lógica Integral de Nutrición
 * Consolidado: Cálculos Master + Gráficos + UI
 */

// --- 1. CONSTANTES DE CÁLCULO (Sincronizadas con Python) ---
const N_CONST = {
    VEG_G_POR: 5,
    FRUIT_G_POR: 14,
    LACT_CARB_POR: 7,
    LACT_PROT_POR: 6.5,
    CAL_PER_CARB: 4,
    CAL_PER_PROT: 4,
    CAL_PER_FAT: 9,
    SVG_DASH: 157.1 // 2 * PI * 25
};

// --- 2. FUNCIÓN MAESTRA DE CÁLCULOS ---
function calculateNutrition() {
    const calEl = document.querySelector('[data-key="calorias_diarias"]');
    if (!calEl) return;

    const calories = parseFloat(calEl.innerText) || 0;
    const dietType = (document.getElementById('vegetariano')?.value || document.getElementById('vegetariano')?.innerText || 'No').trim();
    const consumesEggs = (document.getElementById('consumo_leche_huevos')?.value || document.getElementById('consumo_leche_huevos')?.innerText || 'No').trim();

    // A. Macros Totales (55% / 15% / 30%)
    const totalCarbGrams = (calories * 0.55) / N_CONST.CAL_PER_CARB;
    const totalProtGrams = (calories * 0.15) / N_CONST.CAL_PER_PROT;
    const totalFatGrams = (calories * 0.30) / N_CONST.CAL_PER_FAT;

    // B. Vegetales (Porciones según calorías)
    let vPor = 0;
    if (calories <= 1600) vPor = 3;
    else if (calories <= 2000) vPor = 4;
    else if (calories <= 2400) vPor = 5;
    else if (calories <= 2800) vPor = 6;
    else vPor = 7;

    // C. Frutas (Porciones según calorías)
    let fPor = 0;
    if (calories <= 1800) fPor = 3;
    else if (calories <= 2400) fPor = 4;
    else fPor = 5;

    // D. Lácteos (>1199? 3 : 2)
    const lPor = calories > 1199 ? 3 : 2;

    // E. Reparto de Carbohidratos
    const vegCarb = vPor * N_CONST.VEG_G_POR;
    const fruitCarb = fPor * N_CONST.FRUIT_G_POR;
    const lactCarb = lPor * N_CONST.LACT_CARB_POR;
    const netCarbs = totalCarbGrams - vegCarb - fruitCarb - lactCarb;
    const gEntero = netCarbs * 0.55;
    const gRefinado = netCarbs * 0.45;

    // F. Reparto de Proteínas
    const protLact = lPor * N_CONST.LACT_PROT_POR;
    const netProt = totalProtGrams - protLact;
    
    let animalProt = 0;
    let vegProt = 0;

    if (dietType === 'Sí') {
        if (consumesEggs === 'Sí') {
            animalProt = netProt * 0.12;
            vegProt = netProt * 0.78;
        } else {
            animalProt = 0;
            vegProt = netProt;
        }
    } else {
        animalProt = netProt * 0.40;
        vegProt = netProt * 0.60;
    }

    // G. Grasas Recomendadas
    const grasasRec = totalFatGrams * 0.75;

    // --- ACTUALIZAR UI ---
    updateUI('gramos_carbohidratos', totalCarbGrams);
    updateUI('porciones_vegetales', vPor);
    updateUI('gramos_vegetales', vegCarb);
    updateUI('porciones_fruta', fPor);
    updateUI('gramos_frutas', fruitCarb);
    updateUI('gramos_grano_entero', gEntero);
    updateUI('gramos_grano_refinado', gRefinado);

    updateUI('gramos_proteina_total', totalProtGrams);
    updateUI('porciones_lacteos', lPor);
    updateUI('gramos_proteina_animal', animalProt);
    updateUI('gramos_proteina_vegetal', vegProt);

    updateUI('gramos_grasa', totalFatGrams);
    updateUI('grasas_recomendadas', grasasRec);

    // Actualizar gráfico de torta
    renderMacrosChart(totalCarbGrams, totalProtGrams, totalFatGrams);
}

function updateUI(key, value) {
    const el = document.querySelector(`[data-key="${key}"]`);
    if (el && !el.matches(':focus')) {
        el.innerText = Math.round(value);
    }
}

// --- 3. LÓGICA DEL GRÁFICO SVG ---
function renderMacrosChart(carbs, prot, fat) {
    const totalCal = (carbs * N_CONST.CAL_PER_CARB) + (prot * N_CONST.CAL_PER_PROT) + (fat * N_CONST.CAL_PER_FAT);
    if (totalCal <= 0) return;

    const pCarb = ((carbs * N_CONST.CAL_PER_CARB) / totalCal) * 100;
    const pProt = ((prot * N_CONST.CAL_PER_PROT) / totalCal) * 100;
    const pFat = ((fat * N_CONST.CAL_PER_FAT) / totalCal) * 100;

    const cDash = (pCarb / 100) * N_CONST.SVG_DASH;
    const prDash = (pProt / 100) * N_CONST.SVG_DASH;
    const fDash = (pFat / 100) * N_CONST.SVG_DASH;

    const carbArc = document.getElementById('macro-carb-arc');
    if (carbArc) carbArc.style.strokeDasharray = `${cDash} ${N_CONST.SVG_DASH}`;

    const protArc = document.getElementById('macro-prot-arc');
    if (protArc) {
        protArc.style.strokeDasharray = `${prDash} ${N_CONST.SVG_DASH}`;
        protArc.style.strokeDashoffset = -cDash;
    }

    const fatArc = document.getElementById('macro-fat-arc');
    if (fatArc) {
        fatArc.style.strokeDasharray = `${fDash} ${N_CONST.SVG_DASH}`;
        fatArc.style.strokeDashoffset = -(cDash + prDash);
    }

    // Porcentajes en leyenda
    if (document.getElementById('legend-carb-pct')) document.getElementById('legend-carb-pct').innerText = Math.round(pCarb) + '%';
    if (document.getElementById('legend-prot-pct')) document.getElementById('legend-prot-pct').innerText = Math.round(pProt) + '%';
    if (document.getElementById('legend-fat-pct')) document.getElementById('legend-fat-pct').innerText = Math.round(pFat) + '%';
}

// --- 4. EVENT LISTENERS Y UI ---
document.addEventListener('DOMContentLoaded', () => {

    // A. Sliders de Preferencias
    document.querySelectorAll('.food-preference input[type="range"]').forEach(slider => {
        slider.addEventListener('input', function () {
            const display = document.getElementById(this.id + '-value');
            if (display) display.textContent = this.value;

            const pct = (this.value - this.min) / (this.max - this.min) * 100;
            this.style.background = `linear-gradient(to right, #0e647d ${pct}%, rgba(255,255,255,0.1) ${pct}%)`;
        });
        slider.dispatchEvent(new Event('input'));
    });

    // B. Lógica de visibilidad Vegetariano
    const vegSelect = document.getElementById('vegetariano');
    if (vegSelect) {
        // Si el elemento es un td, no tiene evento 'change' pero podemos observar cambios si se hiciera editable
        // Por ahora calula al inicio
    }

    // C. Escuchar cambios en Calorías (ContentEditable)
    const calInput = document.querySelector('[data-key="calorias_diarias"]');
    if (calInput) {
        calInput.addEventListener('input', calculateNutrition);
    }

    // D. Botón Guardar
    document.getElementById('btn-guardar-nutricion')?.addEventListener('click', async function () {
        const btn = this;
        btn.disabled = true;
        const originalText = btn.innerText;
        btn.innerText = "Guardando...";

        const data = { id: btn.getAttribute('data-paciente-id') };
        document.querySelectorAll('[data-key]').forEach(el => {
            data[el.getAttribute('data-key')] = el.innerText.trim();
        });

        try {
            const resp = await fetch('/update_submission', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            alert(resp.ok ? "✓ Cambios guardados" : "❌ Error al guardar");
        } catch (e) {
            alert("❌ Error de conexión");
        } finally {
            btn.innerText = originalText;
            btn.disabled = false;
        }
    });

    // E. Inicialización
    calculateNutrition();
});