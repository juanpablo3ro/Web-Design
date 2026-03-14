/**
 * ============================================================
 * 1. UTILIDADES Y TRADUCTORES
 * ============================================================
 */
function rToS(val) {
    const m = {
        'Para nada': 0,
        'Algunos días': 1,
        'Más de la mitad de los días': 2,
        'Casi todos los días': 3
    };
    return m[val] || 0;
}

/**
 * Helper para actualizar texto de un elemento si existe
 */
function safeSet(id, val) {
    const el = document.getElementById(id);
    if (el) el.innerText = val;
}

/**
 * ============================================================
 * 2. INICIALIZACIÓN Y FLUJO PRINCIPAL
 * ============================================================
 */
document.addEventListener('DOMContentLoaded', async function () {
    const pathParts = window.location.pathname.split('/');
    const subId = pathParts[pathParts.length - 1];

    if (!subId || isNaN(subId)) return;

    try {
        const response = await fetch(`/get_submission/${subId}`);
        if (!response.ok) throw new Error("No se pudo obtener la información");

        const d = await response.json();

        // --- CÁLCULOS TRANSVERSALES ---
        const peso = parseFloat(d.peso_kg) || 0;
        const talla = parseFloat(d.talla_cm) || 0;
        const imcCalculado = (peso > 0 && talla > 50) ? (peso / ((talla / 100) ** 2)) : 0;

        // --- 1. LLENADO DE SECCIONES (DATOS Y TEXTO) ---
        actualizarDatosGenerales(d);
        actualizarSeccionAntecedentes(d);
        actualizarSeccionMedicación(d);
        actualizarEstiloVida(d);
        actualizarSaludMental(d);
        actualizarReporteAntropometrico(d, imcCalculado);

        // --- 2. MOTORES DE DIAGNÓSTICO Y LABORATORIO ---
        actualizarLaboratorio(d);
        actualizarComplicaciones(d);

        if (typeof actualizarDiagnosticosYRiesgos === 'function') {
            actualizarDiagnosticosYRiesgos(d, imcCalculado);
        }
        if (typeof actualizarAHAScore === 'function') {
            actualizarAHAScore(d, imcCalculado);
        }
        if (typeof actualizarRecomendacionesVida === 'function') {
            actualizarRecomendacionesVida(d, imcCalculado);
        }

        // --- 3. RENDERIZACIÓN DE GRÁFICOS (GAUGES) ---
        if (typeof renderizarGraficoIMC === 'function') renderizarGraficoIMC(peso, talla);
        if (typeof renderizarGraficoAbdominal === 'function') {
            renderizarGraficoAbdominal(parseFloat(d.perimetro_abdominal) || 0, d.sexo);
        }
        if (typeof renderizarGraficoPAS === 'function') {
            renderizarGraficoPAS(parseFloat(d.presion_sistolica) || 0, parseFloat(d.presion_diastolica) || 0, d.medicamento_presion);
        }

        // --- 4. SELECTOR Y EDICIÓN (Protegido contra errores) ---
        const selectEl = document.getElementById('participantSelect');
        if (selectEl) {
            // Solo intentamos cargar si la función existe
            if (typeof cargarParticipantesEnSelector === 'function') {
                await cargarParticipantesEnSelector(selectEl, subId);
                selectEl.onchange = function () {
                    if (this.value) window.location.href = '/reporte/' + this.value;
                };
            } else {
                console.warn("Aviso: cargarParticipantesEnSelector no está definida. Saltando selector.");
            }
        }
        if (typeof vincularListenersEdicion === 'function') vincularListenersEdicion();

    } catch (err) {
        console.error("Error crítico en el reporte:", err);
    }
});

/**
 * ============================================================
 * 2. FUNCIONES DE SECCIÓN (SEGMENTOS 1-5)
 * ============================================================
 */

// SEGMENTO 1: DATOS GENERALES
function actualizarDatosGenerales(d) {
    const campos = {
        'paciente-nombre-completo': `${d.nombre || ''} ${d.apellidos || ''}`,
        'paciente-id': `ID: ${d.id || '2026-DEMO'}`,
        'fecha-reporte': d.fecha_registro || '--',
        'p-nombre': d.nombre,
        'p-apellidos': d.apellidos,
        'p-edad': (d.edad || '--') + " años",
        'p-sexo': d.sexo,
        'p-email': d.email,
        'p-ciudad': d.ciudad,
        'p-pais': d.pais
    };

    for (let id in campos) {
        const el = document.getElementById(id);
        if (el) el.innerText = campos[id] || '--';
    }
}

// SEGMENTO 2: ANTECEDENTES (TABLA)
function actualizarSeccionAntecedentes(d) {
    const antArr = ["Diabetes", "Sobrepeso u Obesidad", "Infarto al Corazón o Accidente Cerebrovascular", "Hipertensión", "Colesterol o Triglicéridos Elevados"];
    const antLabels = ["Diabetes", "Sobrepeso/Obesidad", "Infarto o ACV", "Hipertensión", "Lípidos Elevados"];
    const container = document.getElementById('lista-antecedentes');
    if (!container) return;

    container.innerHTML = antArr.map((a, i) => {
        const has = d.antecedentes?.includes(a);
        return `<tr class="border-b border-white/10 last:border-0">
                    <td class="py-2 opacity-80">${antLabels[i]}</td>
                    <td class="text-right font-bold ${has ? 'text-orange-500' : 'opacity-30'} ant-status">${has ? 'Presente' : 'Ausente'}</td>
                </tr>`;
    }).join('');
}

// SEGMENTO 3: MEDICACIÓN (TABLA)
function actualizarSeccionMedicación(d) {
    const medDict = {
        "medicamento_presion": "Antihipertensivos",
        "medicamento_glucosa": "Antidiabéticos",
        "medicamento_lipidos": "Hipolipemiantes",
        "medicamento_peso": "Antiobesidad"
    };
    const container = document.getElementById('lista-medicacion');
    if (!container) return;

    container.innerHTML = Object.entries(medDict).map(([k, v]) => {
        const has = d[k] === 'Sí';
        const idMap = {
            "medicamento_presion": "h-med-presion",
            "medicamento_glucosa": "h-med-glucosa",
            "medicamento_lipidos": "h-med-lipidos",
            "medicamento_peso": "h-med-peso"
        };
        return `<tr class="border-b border-white/10 last:border-0">
                    <td class="py-2 opacity-80">${v}</td>
                    <td id="${idMap[k]}" class="text-right font-bold ${has ? 'text-green-500' : 'opacity-30'}">${has ? 'Sí' : 'No'}</td>
                </tr>`;
    }).join('');
}

/**
 * ============================================================
 * SEGMENTO 4: ESTILO DE VIDA Y NUTRICIÓN
 * ============================================================
 */
function actualizarEstiloVida(d) {
    const nutriIds = {
        'h-frutas': d.raciones_frutas || '0',
        'h-vegetales': d.raciones_vegetales || '0',
        'h-granos': d.raciones_grano_entero || '0',
        'h-pescado': d.raciones_pescado || '0',
        'h-azucar': d.vasos_bebidas_azucaradas || '0',
        'h-lacteos': d['frecuencia-lacteos'] || d.frecuencia_lacteos || '0',
        // Nueva captura para carnes
        'h-carnes': d['frecuencia-carnes'] || d.frecuencia_carnes || '0',
        'h-sal': d.habitos_sal || '0'
    };

    for (const [id, val] of Object.entries(nutriIds)) {
        safeSet(id, val || '0');
    }

    // Nivel de Actividad (Segmento 6)
    safeSet('h-nivel-actividad', d['nivel-actividad'] || d.nivel_actividad || '--');

    // 2. Lógica de Sal (Criterio AHA simplificado)
    const salHabitos = d.habitos_sal || "";
    const opcionesSaludables = [
        "Evito comer comidas procesadas",
        "Raramente como afuera",
        "Evito la sal cuando estoy cocinando"
    ];
    // Contamos cuántas opciones saludables seleccionó el paciente
    const countSaludables = opcionesSaludables.filter(opt => salHabitos.includes(opt)).length;

    const hSal = document.getElementById('h-sal');
    if (hSal) {
        hSal.innerText = countSaludables >= 2 ? "Bajo en Sal" : "Consumo Regular";
    }

    // 3. Otros Hábitos (Sin asunciones, solo datos reales)
    const otros = {
        'h-alcohol': d.frecuencia_alcohol || 'No contestó',

        // Capturamos la cantidad buscando ambas variantes de nombre
        'h-alcohol-cant': d['cantidad-alcohol'] || d.cantidad_alcohol || 'No contestó',

        'h-actividad': d.nivel_actividad
            ? `${d.nivel_actividad} (${d.minutos_actividad_semana || '0'} min/sem)`
            : 'No contestó',

        'h-tabaco': d.habito_tabaquico || 'No contestó',

        'h-sueno-pts': d.puntuacion_sueno
            ? d.puntuacion_sueno + "/10"
            : 'N/A',

        'h-ronca': d.ronca || 'No contestó'
    };

    // Renderizado con estilo para datos faltantes
    for (const [id, val] of Object.entries(otros)) {
        const el = document.getElementById(id);
        if (el) {
            el.innerText = val;
            // Estilo visual si no hay respuesta
            if (val === 'No contestó' || val === 'N/A') {
                el.style.opacity = "0.5";
                el.style.fontWeight = "normal";
            } else {
                el.style.opacity = "1";
                el.style.fontWeight = "bold";
            }
        }
    }

    // 4. Puntaje Alimentación
    // Aseguramos que d.raciones_frutas etc. sean tratados como números
    let score = (parseFloat(d.raciones_frutas || 0) >= 3 ? 1 : 0) +
        (parseFloat(d.raciones_vegetales || 0) >= 4 ? 1 : 0) +
        (parseFloat(d.raciones_grano_entero || 0) >= 2 ? 1 : 0) +
        (parseFloat(d.raciones_pescado || 0) >= 2 ? 1 : 0) +
        (parseFloat(d.vasos_bebidas_azucaradas || 0) <= 1 ? 1 : 0) +
        (countSaludables >= 2 ? 1 : 0);

    // Mandar a renderizar (Esta función ahora es infalible con tus IDs)
    renderizarGraficoAlimentacion(score);
}

/**
 * Renderiza el gráfico de alimentación basado en el score (0-6)
 * Versión con Fondo Transparente y Glow sincronizado
 */
function renderizarGraficoAlimentacion(score) {
    const maxScore = 6;
    let categoria = "Pobre";
    let color = "#ef4444"; // Rojo

    if (score >= 5) {
        categoria = "Excelente";
        color = "#10b981"; // Verde
    } else if (score >= 3) {
        categoria = "Moderada";
        color = "#f59e0b"; // Naranja
    }

    // 1. Mover la barra con efecto Neón
    const bar = document.getElementById('alim-gauge-bar');
    if (bar) {
        const fullLength = 110;
        const percentage = Math.min((score / maxScore) * 100, 100);

        bar.style.stroke = color;
        bar.style.filter = `drop-shadow(0 0 5px ${color}88)`;
        bar.style.strokeDasharray = `${(percentage / 100) * fullLength} ${fullLength}`;
    }

    // 2. Glow dinámico (Fondo transparente, solo brilla el aura)
    const glow = document.getElementById('alim-glow');
    if (glow) {
        glow.style.backgroundColor = color;
        glow.style.opacity = "0.3"; // Opacidad sutil
        glow.style.boxShadow = `0 0 40px 10px ${color}22`;
    }

    // 3. Textos con sombras suaves
    const valText = document.getElementById('val-puntaje-alim');
    if (valText) {
        valText.innerText = score;
        valText.style.color = "white"; // Número en blanco para legibilidad
        valText.style.textShadow = `0 0 10px ${color}88`;
    }

    const lblBadge = document.getElementById('label-categoria-alim');
    if (lblBadge) {
        lblBadge.innerText = categoria;
        lblBadge.style.color = color;
        lblBadge.style.backgroundColor = "transparent"; // Forzamos transparencia
        lblBadge.style.borderColor = color + '44';
    }
}

// SEGMENTO 5: SALUD MENTAL
function actualizarSaludMental(d) {


    const ans = rToS(d.ansiedad_nervios) + rToS(d.control_preocupacion);
    const dep = rToS(d.poco_interes) + rToS(d.sentimiento_deprimido);

    const config = [
        { id: 'val-m-ans', val: ans, critico: ans >= 3 },
        { id: 'val-m-dep', val: dep, critico: dep >= 3 },
        { id: 'val-m-qol', val: d.escala_salud_hoy, critico: parseFloat(d.escala_salud_hoy) < 60 },
        { id: 'val-m-opt', val: d.nivel_optimismo, critico: false },
        { id: 'val-m-pes', val: d.nivel_pesimismo, critico: false }
    ];

    config.forEach(item => {
        const el = document.getElementById(item.id);
        if (el) {
            el.innerText = item.val || '--';
            el.classList.toggle('text-orange-500', item.critico);
        }
    });
}

// ADICIONAL: REPORTE ANTROPOMÉTRICO (SEGMENTO PESO/METAS)
function actualizarReporteAntropometrico(d, imc) {
    // 2. LLENADO DE CAMPOS BÁSICOS
    safeSet('p-peso', d.peso_kg);
    safeSet('p-talla', d.talla_cm);
    safeSet('p-cintura', d.perimetro_abdominal);
    safeSet('p-presion-sistolica', d.presion_sistolica);
    safeSet('p-presion-diastolica', d.presion_diastolica);
    safeSet('p-cuello', d.circunferencia_cuello);
    safeSet('p-imc', imc ? imc.toFixed(1) : '--');

    // 3. ¡CONEXIÓN CRÍTICA!: DISPARAR LOS GRÁFICOS (GAUGES)
    // Esto quita el mensaje de "calculando" y mueve las agujas
    renderizarGraficoIMC(d.peso_kg, d.talla_cm);
    renderizarGraficoAbdominal(d.perimetro_abdominal, d.sexo);
    renderizarGraficoPAS(d.presion_sistolica, d.presion_diastolica, d.medicamento_presion);
}
/**
 * ============================================================
 * 6. SISTEMA DE GAUGES Y LISTENERS DE EDICIÓN
 * ============================================================
 */

/**
 * Lógica Maestra para Gauges (Versión Optimizada para Glow y Neón)
 * Sustituye completamente la función anterior para activar los efectos visuales.
 */
const updateMiniGauge = (idPrefix, value, max, label, color = "#ED7D30") => {
    // 1. Selección de elementos
    const bar = document.getElementById(`${idPrefix}-gauge-bar`);
    const valText = document.getElementById(`${idPrefix}-gauge-val`) || document.getElementById(`${idPrefix}-val`);
    const lblBadge = document.getElementById(`${idPrefix}-gauge-label`) || document.getElementById(`${idPrefix}-label`);
    const glow = document.getElementById(`glow-${idPrefix}`);

    // 2. Actualización de Textos y Colores de etiqueta
    if (valText) valText.innerText = value;
    if (lblBadge) {
        lblBadge.innerText = label;
        lblBadge.style.color = color;
        lblBadge.style.borderColor = color + '44'; // Borde sutil transparente
    }

    // 3. Animación de la Barra de Progreso con efecto Drop-Shadow (Neón)
    if (bar) {
        const fullLength = 110;
        const percentage = Math.min((value / max) * 100, 100);
        const dashValue = (percentage / 100) * fullLength;

        bar.style.stroke = color;
        // Aplicamos un brillo directamente al trazo del SVG
        bar.style.filter = `drop-shadow(0 0 5px ${color}88)`;
        bar.style.transition = "stroke-dasharray 1.2s cubic-bezier(0.4, 0, 0.2, 1), stroke 0.6s ease";
        bar.style.strokeDasharray = `${dashValue} ${fullLength}`;
    }

    // 4. Efecto de Brillo de Fondo (Glow) dinámico
    if (glow) {
        glow.style.backgroundColor = color;
        glow.style.opacity = "0.35"; // Aumentamos un poco la intensidad
        // Creamos una sombra difusa que expande el color
        glow.style.boxShadow = `0 0 40px 10px ${color}33`;
    }
};

// Renderizadores Específicos
const renderizarGraficoIMC = (peso, talla) => {
    const p = parseFloat(peso) || 0;
    const t = parseFloat(talla) || 0;
    if (p > 5 && t > 50) {
        const imc = parseFloat((p / ((t / 100) ** 2)).toFixed(1));
        let cat = "Normal", col = "#10b981";
        if (imc < 18.5) { cat = "Bajo Peso"; col = "#60a5fa"; }
        else if (imc < 30) { cat = imc < 25 ? "Normal" : "Sobrepeso"; col = imc < 25 ? "#10b981" : "#f59e0b"; }
        else { cat = "Obesidad"; col = "#ef4444"; }
        updateMiniGauge('imc', imc, 45, cat, col);
        if (document.getElementById('p-imc')) document.getElementById('p-imc').innerText = imc;
    }
};

const renderizarGraficoAbdominal = (valor, sexo) => {
    const v = parseFloat(valor) || 0;
    const limite = (sexo === 'Masculino') ? 90 : 86;
    updateMiniGauge('abd', v, 130, v >= limite ? "Presente" : "Normal", v >= limite ? "#ef4444" : "#10b981");
};

const renderizarGraficoPAS = (pas, pad, medicado) => {
    const vPas = parseFloat(pas) || 0;
    const vPad = parseFloat(pad) || 0;
    let diag = "Normal", col = "#10b981";
    if (vPas >= 140 || vPad >= 90) { diag = "Hipertensión"; col = "#ef4444"; }
    else if (vPas >= 130 || vPad >= 80) { diag = "Alta"; col = "#f59e0b"; }
    else if (vPas >= 120) { diag = "Elevada"; col = "#fbbf24"; }
    if (medicado === "Sí") diag = "Tratada";
    updateMiniGauge('pas', vPas, 200, diag, col);
};

// Listener unificado para recálculos inmediatos al editar
const vincularListenersEdicion = () => {
    // Al editar campos de nutrición
    const nutriIds = ['h-frutas', 'h-vegetales', 'h-granos', 'h-pescado', 'h-azucar', 'h-sal'];
    nutriIds.forEach(id => {
        document.getElementById(id)?.addEventListener('input', () => {
            const extraer = (i) => parseFloat(document.getElementById(i)?.innerText) || 0;
            let score = (extraer('h-frutas') >= 3 ? 1 : 0) + (extraer('h-vegetales') >= 4 ? 1 : 0) +
                (extraer('h-granos') >= 2 ? 1 : 0) + (extraer('h-pescado') >= 2 ? 1 : 0) +
                (extraer('h-azucar') <= 1 ? 1 : 0);
            const sal = document.getElementById('h-sal')?.innerText.toLowerCase() || "";
            if (sal.includes('bajo')) score++;
            renderizarGraficoAlimentacion(score);
        });
    });

    // Al editar campos físicos
    const antropoIds = ['p-peso', 'p-talla', 'p-cintura', 'p-presion-sistolica', 'p-presion-diastolica'];
    antropoIds.forEach(id => {
        document.getElementById(id)?.addEventListener('input', () => {
            const p = parseFloat(document.getElementById('p-peso').innerText) || 0;
            const t = parseFloat(document.getElementById('p-talla').innerText) || 0;
            const abd = parseFloat(document.getElementById('p-cintura').innerText) || 0;
            const pas = parseFloat(document.getElementById('p-presion-sistolica').innerText) || 0;
            const pad = parseFloat(document.getElementById('p-presion-diastolica').innerText) || 0;
            const sexo = document.getElementById('p-sexo')?.innerText || 'Masculino';
            const med = document.querySelector('[data-key="medicamento_presion"]')?.innerText || 'No';
            renderizarGraficoIMC(p, t);
            renderizarGraficoAbdominal(abd, sexo);
            renderizarGraficoPAS(pas, pad, med);
        });
    });
};

/**
 * ============================================================
 * 7. LABORATORIO Y QUÍMICA SANGUÍNEA
 * ============================================================
 */
function actualizarLaboratorio(d) {
    const total = parseFloat(d.colesterol_total);
    const hdl = parseFloat(d.colesterol_hdl);
    const noHdl = (!isNaN(total) && !isNaN(hdl)) ? (total - hdl) : null;

    const lab = [
        ["Glucosa Ayunas", d.glucosa_ayunas, "mg/dL", v => v >= 100, "glucosa_ayunas"],
        ["HbA1c", d.hba1c, "%", v => v >= 5.7, "hba1c"],
        ["Colesterol Total", d.colesterol_total, "mg/dL", v => v >= 200, "colesterol_total"],
        ["Colesterol LDL", d.colesterol_ldl, "mg/dL", v => v >= 130, "colesterol_ldl"],
        ["Colesterol HDL", d.colesterol_hdl, "mg/dL", v => v < 40, "colesterol_hdl"],
        ["Triglicéridos", d.trigliceridos, "mg/dL", v => v >= 150, "trigliceridos"],
        ["Col. No HDL", noHdl !== null ? noHdl : '--', "mg/dL", v => v >= 130, "no_hdl_calc"]
    ];

    const container = document.getElementById('datos-lab');
    if (container) {
        container.innerHTML = lab.map(([label, val, unit, check, key]) => {
            const esAlerta = val !== '--' && val !== null && check(parseFloat(val));
            const idMap = {
                "glucosa_ayunas": "p-glucosa",
                "hba1c": "p-hba1c",
                "colesterol_total": "p-col-total",
                "colesterol_ldl": "p-col-ldl",
                "colesterol_hdl": "p-col-hdl",
                "trigliceridos": "p-trigliceridos"
            };
            return `<tr>
                <td class="data-label pt-2">${label}</td>
                <td id="${idMap[key] || ''}" class="text-right pt-2 font-bold editable-field ${esAlerta ? 'text-orange-500 font-black' : ''}" 
                    contenteditable="true" data-key="${key}">${val || '--'}</td>
                <td class="text-xs opacity-50 pt-2 pl-1">${unit}</td>
            </tr>`;
        }).join('');
    }

    // Sincronizar diagnóstico de lípidos si existe la función
    if (typeof Diagnosticos !== 'undefined' && typeof actualizarDiagnosticosYRiesgos === 'function') {
        const dLip = Diagnosticos.lipidos(d);
        const resLip = document.getElementById('diag-lipidos'); // ID correcto según el HTML
        if (resLip) {
            resLip.innerText = dLip.label;
            resLip.className = `p-2 text-right font-bold ${dLip.color}`;
        }
    }
}

/**
 * ============================================================
 * 8. COMPLICACIONES (GRID DE SALUD)
 * ============================================================
 */
function actualizarComplicaciones(d) {
    const compDict = {
        "Infarto": "Infarto / Angina",
        "Accidente": "ACV",
        "Arritmia": "Arritmia",
        "Crecimiento": "Hipertrofia Vent.",
        "Insuficiencia": "Insuf. Cardíaca",
        "Artrosis": "Artrosis / Dolor",
        "Nefropatía": "Daño Renal",
        "Neuropatía": "Daño Nervioso",
        "visión": "Daño Visual"
    };

    const userEnf = (d.enfermedades_presentadas || "").toLowerCase();
    const container = document.getElementById('grid-complicaciones');
    if (!container) return;

    container.innerHTML = Object.entries(compDict).map(([k, v]) => {
        const has = userEnf.includes(k.toLowerCase());
        return `
            <div class="glass-card text-center p-3 border transition-all ${has ? 'bg-orange-500/10 border-orange-500/50' : 'border-white/5 opacity-60'}">
                <p class="data-label text-xs uppercase tracking-wider mb-1">${v}</p>
                <p class="text-sm font-bold ${has ? 'text-orange-500' : 'text-white/20'}">
                    ${has ? 'DETECTADO' : 'AUSENTE'}
                </p>
            </div>`;
    }).join('');
}
/**
 * ============================================================
 * 9. MOTORES DE DIAGNÓSTICO (Cerebro Lógico)
 * Centraliza los criterios médicos para evitar discrepancias.
 * ============================================================
 */
const Diagnosticos = {
    nutricional: (imc) => {
        if (!imc || imc === 0) return { label: "Sin datos", alt: false, color: 'text-gray-400' };
        if (imc < 18.5) return { label: "Bajo peso", alt: true, color: 'text-blue-400' };
        if (imc < 25) return { label: "Normal", alt: false, color: 'text-green-500' };
        if (imc < 30) return { label: "Sobrepeso", alt: true, color: 'text-orange-500' };
        return { label: "Obesidad", alt: true, color: 'text-red-500' };
    },

    lipidos: (d) => {
        const ldl = parseFloat(d.colesterol_ldl), tri = parseFloat(d.trigliceridos);
        const hdl = parseFloat(d.colesterol_hdl), tot = parseFloat(d.colesterol_total);
        const tomaMed = (d.medicamento_lipidos === "Sí");

        const esAlt = (tot >= 200 || ldl >= 130 || tri >= 150 || (d.sexo === 'Masculino' ? hdl < 40 : hdl < 50));

        let label = esAlt ? "Dislipidemia" : "Normal";
        if (tomaMed) label += " (Tratada)";
        if (isNaN(tot) && isNaN(ldl)) label = "Pendiente";

        return { label, alt: esAlt || tomaMed, color: (esAlt || tomaMed) ? 'text-orange-500' : 'text-green-500' };
    },

    glucosa: (d) => {
        const glu = parseFloat(d.glucosa_ayunas);
        const hba1c = parseFloat(d.hba1c);
        const tratada = (d.medicamento_glucosa === "Sí");

        if (isNaN(glu)) return { label: "Pendiente diagnóstico", alt: false, color: "text-gray-400" };

        if (tratada) {
            if (glu >= 140 || hba1c >= 7)
                return { label: "Diabetes tratada no controlada", alt: true, color: "text-red-600" };
            if (glu < 140 && hba1c < 7)
                return { label: "Diabetes tratada y controlada", alt: true, color: "text-green-500" };
        }

        if (!tratada && (glu >= 126 || hba1c >= 6.5))
            return { label: "Diabetes sin tratamiento", alt: true, color: "text-red-500" };

        if (glu >= 100 || hba1c >= 5.7)
            return { label: "Prediabetes", alt: true, color: "text-orange-500" };

        return { label: "Normal", alt: false, color: "text-green-500" };
    },

    hipertension: (d) => {
        const pas = parseFloat(d.presion_sistolica), pad = parseFloat(d.presion_diastolica);
        const tomaMed = (d.medicamento_presion === "Sí");

        // Determinamos si el paciente tiene Diabetes (por tratamiento o valores previos)
        const tieneDiabetes = (d.medicamento_glucosa === "Sí" ||
            parseFloat(d.glucosa_ayunas) >= 126 ||
            parseFloat(d.hba1c) >= 6.5);

        if (isNaN(pas)) return { label: "Pendiente", alt: false, color: 'text-gray-400' };

        // 1. NIVEL CRÍTICO (Grado 2 o superior)
        if (pas >= 140 || pad >= 90) {
            return {
                label: tomaMed ? "HTA No Controlada" : "Hipertensión Controlada",
                alt: true,
                color: 'text-red-500'
            };
        }

        // 2. NIVEL ELEVADO (Basado en riesgo por Diabetes)
        if (pas >= 130 || pad >= 80) {
            if (tieneDiabetes) {
                // Si tiene diabetes, 130/80 ya se considera No Controlada
                return { label: "HTA No Controlada (Paciente con diabetes)", alt: true, color: 'text-red-500' };
            }
            // Si no tiene diabetes, se mantiene como Elevada
            return { label: tomaMed ? "HTA Controlada (No Optima)" : "Presión Arterial Elevada", alt: true, color: 'text-orange-500' };
        }

        // 3. NIVEL NORMAL / CONTROLADO
        if (tomaMed) {
            if (tieneDiabetes) {
                return { label: "HTA Controlada (Paciente con diabetes)", alt: true, color: 'text-green-500' };
            }
            return { label: "HTA Controlada (Paciente con diabetes)", alt: true, color: 'text-blue-400' };
        }

        return { label: "Presión Arterial Normal", alt: false, color: 'text-green-500' };
    },

    apnea: (d) => {
        let p = 0;
        const imc = parseFloat(d.peso_kg) / ((parseFloat(d.talla_cm) / 100) ** 2) || 0;
        // Criterios NoSAS simplificados
        if ((d.sexo === "Masculino" && d.circunferencia_cuello >= 40) || (d.sexo === "Femenino" && d.circunferencia_cuello >= 38)) p += 4;
        if (imc >= 30) p += 5; else if (imc >= 25) p += 3;
        if (d.ronca === "Sí") p += 2;
        if (parseInt(d.edad) > 55) p += 4;
        if (d.sexo === "Masculino") p += 2;

        return { score: p, alt: p >= 8, label: p >= 8 ? "Riesgo Alto" : "Riesgo Bajo" };
    },

    riesgoBio: (d) => {
        const has = (d.antecedentes && d.antecedentes.length > 0);
        return { label: has ? "Presente" : "Ausente", alt: has };
    },

    tabaquismo: (d) => {
        const val = d.habito_tabaquico;
        let label = "No contestó", alt = false;
        if (val === "Actualmente fumo" || val === "Dejé de fumar hace menos de 1 año") { label = "Fumador"; alt = true; }
        else if (val === "Dejé de fumar hace más de 1 año") { label = "Exfumador"; alt = false; }
        else if (val === "Nunca he fumado") { label = "No fuma"; alt = false; }
        return { label, alt };
    },

    fumadorPasivo: (d) => {
        const has = (d['exposicion-humo'] === "Sí, fuman en mi presencia");
        return { label: has ? "Presente" : "Ausente", alt: has };
    },

    actividad: (d) => {
        const nivel = d['nivel-actividad'] || d.nivel_actividad || "";
        let label = "Baja", alt = true;
        if (nivel === "Muy Activo") { label = "Alta"; alt = false; }
        else if (nivel === "Moderadamente Activo") { label = "Moderada"; alt = false; }
        return { label, alt };
    },

    alcohol: (d) => {
        const val = d.frecuencia_alcohol || "";
        const has = val.includes("4 o más");
        return { label: val || "Social/Nulo", alt: has };
    },

    sueno: (d) => {
        const ok = (parseInt(d.puntuacion_sueno) >= 7);
        return { label: ok ? "Saludable" : "Deficiente", alt: !ok };
    },

    ansiedad: (d) => {
        const score = (rToS(d.ansiedad_nervios) + rToS(d.control_preocupacion)) || 0;
        return { label: score >= 3 ? "Elevada" : "Baja", alt: score >= 3 };
    },

    depresion: (d) => {
        const score = (rToS(d.poco_interes) + rToS(d.sentimiento_deprimido)) || 0;
        return { label: score >= 3 ? "Elevada" : "Baja", alt: score >= 3 };
    },

    obesidadAbd: (d) => {
        const v = parseFloat(d.perimetro_abdominal) || 0;
        const limite = (d.sexo === 'Masculino') ? 90 : 86;
        const has = v >= limite;
        return { label: has ? "Riesgo Aumentado" : "Normal", alt: has };
    }
};

// SEGMENTO MÓVIL: Las etiquetas de nivel de actividad se sincronizan en actualizarEstiloVida y actualizarRecomendacionesVida

/**
 * ============================================================
 * 10. ACTUALIZACIÓN DE UI DE DIAGNÓSTICOS Y RIESGOS
 * Mapea los resultados de los motores a los elementos del DOM.
 * ============================================================
 */
function actualizarDiagnosticosYRiesgos(d, imcCalculado) {
    const imc = imcCalculado || 0;

    const safeSetDiag = (id, info) => {
        const el = document.getElementById(id);
        if (el) {
            el.innerText = info.label;
            el.className = `p-2 text-right font-bold ${info.color || (info.alt ? 'text-orange-500' : 'text-green-500')}`;
        }
    };

    // --- SEGMENTO 11: DIAGNÓSTICOS DE FACTORES DE RIESGO ---
    safeSetDiag('res-riesgo-bio', Diagnosticos.riesgoBio(d));
    safeSetDiag('res-tabaquismo', Diagnosticos.tabaquismo(d));
    safeSetDiag('res-fumador-pasivo', Diagnosticos.fumadorPasivo(d));
    safeSetDiag('res-actividad-nivel', Diagnosticos.actividad(d));
    safeSetDiag('res-alcohol', Diagnosticos.alcohol(d));
    safeSetDiag('res-sueno', Diagnosticos.sueno(d));
    safeSetDiag('res-apnea', Diagnosticos.apnea(d));
    safeSetDiag('res-ansiedad', Diagnosticos.ansiedad(d));
    safeSetDiag('res-depresion', Diagnosticos.depresion(d));

    // Dentro de la función de diagnósticos/riesgos
    const dLipRiesgo = Diagnosticos.lipidos(d);

    safeSetDiag('res-lipidos', {
        label: dLipRiesgo.label,
        alt: dLipRiesgo.alt
    });

    // --- SEGMENTO 12: CARDIOMETABÓLICOS ---
    const dNut = Diagnosticos.nutricional(imc);
    const dLip = Diagnosticos.lipidos(d);
    const dGlu = Diagnosticos.glucosa(d);
    const dHta = Diagnosticos.hipertension(d);
    const dAbd = Diagnosticos.obesidadAbd(d);

    safeSetDiag('diag-nutricional', dNut);
    safeSetDiag('diag-lipidos', dLip);
    safeSetDiag('diag-obesidad-abd', dAbd);
    safeSetDiag('diag-glucosa', dGlu);
    safeSetDiag('diag-presion', dHta);

    // --- SINCRONIZACIÓN DE TEXTOS DE APOYO ---
    const updateText = (id, text) => { if (document.getElementById(id)) document.getElementById(id).innerText = text; };
    updateText("diagnostico-glucosa-texto", `Estado actual: ${dGlu.label}`);
    updateText("diagnostico-lipidos-texto", `Perfil: ${dLip.label}`);
    updateText("diagnostico-presion-texto", `Categoría: ${dHta.label}`);
}

/**
 * ============================================================
 * 13. CÁLCULO DE SCORE AHA (Life's Essential 8)
 * Optimizado para CSS Moderno con Glow y Gradientes
 * ============================================================
 */
function actualizarAHAScore(d, imcCalculado) {
    const ahaScores = {};
    const imc = imcCalculado || 0;

    // --- LÓGICA DE CÁLCULO (Se mantiene igual para precisión médica) ---
    const salHabitos = d.habitos_sal || "";
    const evitaSal = salHabitos.includes("Evito comer comidas procesadas") || salHabitos.includes("Evito la sal");

    let nutriPuntos = (parseFloat(d.raciones_frutas || 0) > 2 ? 20 : 0) +
        (parseFloat(d.raciones_vegetales || 0) > 3 ? 20 : 0) +
        (parseFloat(d.raciones_grano_entero || 0) > 2 ? 20 : 0) +
        (parseFloat(d.raciones_pescado || 0) >= 2 ? 20 : 0) +
        (evitaSal ? 20 : 0);
    ahaScores.nutricion = Math.min(nutriPuntos, 100);

    const actMap = {
        "0 minutos": 0, "1 a 29 minutos": 20, "30 a 59 minutos": 40,
        "60 a 89 minutos": 60, "90 a 119 minutos": 80, "120 a 149 minutos": 90,
        "150 o más minutos": 100
    };
    ahaScores.actividad = actMap[d.minutos_actividad_semana] || 0;

    const tabMap = {
        "Nunca he fumado": 100, "Dejé de fumar hace más de 1 año": 100,
        "Dejé de fumar hace menos de 1 año": 25, "Actualmente fumo": 0
    };
    ahaScores.tabaco = tabMap[d.habito_tabaquico] || 100;

    const sPt = parseInt(d.puntuacion_sueno || 0);
    ahaScores.sueno = sPt >= 7 ? 100 : (sPt >= 5 ? 50 : 20);
    ahaScores.peso = (imc >= 18.5 && imc < 25) ? 100 : (imc < 30 ? 70 : 30);

    // --- LÓGICA DE CÁLCULO (Se mantiene igual para precisión médica) ---
    // Puntos Glucosa (Lógica AHA Desconectada)
    const gluVal = parseFloat(d.glucosa_ayunas);
    const hba1cVal = parseFloat(d.hba1c);
    const tratadaGlu = (d.medicamento_glucosa === "Sí");
    if (isNaN(gluVal) && isNaN(hba1cVal)) {
        ahaScores.glucosa = 30;
    } else if (!tratadaGlu && gluVal < 100 && (isNaN(hba1cVal) || hba1cVal < 5.7)) {
        ahaScores.glucosa = 100;
    } else if (!tratadaGlu && (gluVal < 126 || hba1cVal < 6.5)) {
        ahaScores.glucosa = 60;
    } else {
        ahaScores.glucosa = 30; // Diabetes o en tratamiento
    }

    // Puntos Lípidos (AHA Essential 8: No-HDL)
    let scoreLipidos = 0; // Por defecto 0 si no hay datos

    // Verificamos si existen ambos valores antes de calcular
    if (d.colesterol_total && d.colesterol_hdl) {
        const total = parseFloat(d.colesterol_total);
        const hdl = parseFloat(d.colesterol_hdl);
        const noHdl = total - hdl;

        // Lógica de puntuación basada en el valor calculado
        if (noHdl < 130) scoreLipidos = 100;
        else if (noHdl < 160) scoreLipidos = 60;
        else scoreLipidos = 30;
    } else {
        // Si no hay laboratorios, el score es 0
        scoreLipidos = 0;
    }

    ahaScores.lipidos = scoreLipidos;

    // Puntos Presión (Lógica AHA Desconectada)
    const pasVal = parseFloat(d.presion_sistolica);
    const padVal = parseFloat(d.presion_diastolica);
    const tratadaHta = (d.medicamento_presion === "Sí");
    if (isNaN(pasVal)) {
        ahaScores.presion = 40;
    } else if (!tratadaHta && pasVal < 120 && padVal < 80) {
        ahaScores.presion = 100;
    } else if (!tratadaHta && pasVal < 130 && padVal < 80) {
        ahaScores.presion = 70; // Elevada
    } else {
        ahaScores.presion = 40;
    }

    // --- RENDERIZADO VISUAL ---
    const totalAha = Math.round(Object.values(ahaScores).reduce((a, b) => a + b, 0) / 8);
    const color = totalAha >= 80 ? "#10b981" : (totalAha >= 50 ? "#f59e0b" : "#ef4444");

    // 1. Valor Central (Soporta tu clase .value-text-modern)
    const valTotalEl = document.getElementById('val-aha-total');
    if (valTotalEl) valTotalEl.innerText = totalAha;

    // 2. Status Badge (Actualiza color y borde según tu .status-badge-modern)
    const statusEl = document.getElementById('val-aha-status');
    if (statusEl) {
        statusEl.innerText = totalAha >= 80 ? "Salud Óptima" : (totalAha >= 50 ? "Salud Moderada" : "Salud Pobre");
        statusEl.style.color = color;
        statusEl.style.borderColor = color + "44";
        statusEl.style.boxShadow = `0 0 15px ${color}22`;
    }

    // 3. EFECTO GLOW (Conecta con .glow-overlay-modern)
    const glowEl = document.getElementById('glow-aha');
    if (glowEl) {
        glowEl.style.background = color; // Tu CSS tiene el blur(50px) y la opacidad
        glowEl.style.opacity = "0.2"; // Un poco más intenso para que se note
    }

    // 4. Arco SVG (Progreso Progresivo)
    const progressArc = document.getElementById('gauge-progress-aha');
    if (progressArc) {
        const fullLength = 119.5;
        progressArc.style.strokeDasharray = `${(totalAha / 100) * fullLength} ${fullLength}`;
        // Mantiene el gradiente del HTML a menos que el score sea crítico (<30)
        progressArc.style.stroke = totalAha < 30 ? "#ef4444" : "url(#gaugeGradient)";
    }

    // 5. Barras Individuales (Tamaño aumentado y alineación mejorada)
    const labels = {
        nutricion: 'Nutrición', actividad: 'Actividad Física', tabaco: 'Tabaco',
        sueno: 'Sueño', peso: 'Peso (IMC)', glucosa: 'Glucosa',
        lipidos: 'Lípidos (No-HDL)', presion: 'Presión Arterial'
    };

    Object.entries(ahaScores).forEach(([key, val]) => {
        const container = document.getElementById(`item-aha-${key}`);
        if (container) {
            // Usamos tu paleta: Verde (#10b981), Naranja (#f59e0b) y Rojo (#ef4444)
            const itemColor = val >= 80 ? "#10b981" : (val >= 50 ? "#f59e0b" : "#ef4444");

            container.innerHTML = `
                <div class="flex justify-between items-end mb-2">
                    <span class="text-[13px] font-bold uppercase tracking-wider text-black/70">${labels[key]}</span>
                    <span class="text-[14px] font-black" style="color: ${itemColor}">${val} <span class="text-[10px] opacity-50">PTS</span></span>
                </div>
                <div class="w-full bg-white/10 h-2 rounded-full overflow-hidden shadow-inner">
                    <div class="h-full transition-all duration-1000 ease-out" 
                         style="width: ${val}%; background: ${itemColor}; box-shadow: 0 0 12px ${itemColor}66;">
                    </div>
                </div>`;
        }
    });
}

/**
 * ============================================================
 * 12. ACTUALIZACIÓN DE RECOMENDACIONES DE VIDA
 * Unifica: Peso, Metabolismo, Nutrición, Actividad, Tabaco, 
 * Apnea, salud mental, Glucemia y Lípidos.
 * ============================================================
 */
function actualizarRecomendacionesVida(d, imcCalculado) {
    const imc = imcCalculado || 0;

    // 1. --- METABOLISMO Y BALANCE CALÓRICO ---
    const peso = parseFloat(d.peso_kg) || 0;
    const talla = parseFloat(d.talla_cm) || 0;
    const edad = parseInt(d.edad) || 30;

    // Fórmula Mifflin-St Jeor
    let tmb = (10 * peso) + (6.25 * talla) - (5 * edad);
    tmb = (d.sexo === "Masculino") ? tmb + 5 : tmb - 161;

    // Factor de actividad
    const factores = { "Sedentario": 1.2, "Poco Activo": 1.375, "Moderadamente Activo": 1.55, "Muy Activo": 1.725 };
    const factor = factores[d.nivel_actividad] || 1.2;
    const mantenimiento = Math.round(tmb * factor);

    safeSet("mb-peso", Math.round(tmb) + " kcal/día");
    safeSet("val-balance-calorico", mantenimiento + " kcal/día");

    // 2. --- RECOMENDACIÓN DE PESO E IMC ---
    const abdAlt = (d.sexo === 'Masculino' && d.perimetro_abdominal >= 90) ||
        (d.sexo === 'Femenino' && d.perimetro_abdominal >= 86);

    let recPeso;
    if (!imc || imc === 0) {
        recPeso = "Mida su peso corporal para evaluar";
    } else {
        recPeso = (imc < 18.5) ? "Posiblemente debas subir de peso" :
            (imc >= 25 || abdAlt) ? "Bajar peso y grasa corporal" :
                "Mantener peso y grasa corporal normal";
    }
    safeSet("val-rec-peso", d.rec_peso || recPeso);

    // 3. --- LÓGICA DE OBJETIVOS DE PESO ---
    const deseaBajar = (d.desea_bajar_peso === "Sí" || d['desea-bajar-peso'] === "Sí");
    const tablaObj = document.getElementById("tabla-objetivo-peso");

    if (deseaBajar && peso > 0) {
        if (tablaObj) tablaObj.style.display = "grid";

        // Captura de datos
        const pRaw = d['porcentaje-perdida'] || d.porcentaje_perdida || "0";
        const tRaw = d['tiempo-perdida'] || d.tiempo_perdida || "3";

        const porc = parseInt(String(pRaw).replace(/\D/g, '')) || 0;
        const meses = parseInt(String(tRaw).replace(/\D/g, '')) || 3;
        const lossKg = peso * (porc / 100);
        const gramosSemanales = (lossKg / meses / 4) * 1000;

        // Llenado de etiquetas informativas
        safeSet('objetivo-bajar', 'Sí');
        safeSet('objetivo-perdida', porc > 0 ? porc + "%" : "No seleccionado");
        safeSet('objetivo-tiempo', meses + " meses");

        // Llenado de la Tabla de Datos
        safeSet("val-peso-actual", peso + " kg");
        safeSet("val-peso-meta", (peso - lossKg).toFixed(1) + " kg");
        safeSet("val-peso-reducir", lossKg.toFixed(1) + " kg");
        safeSet("val-meses", meses);
        safeSet("val-mensual", (lossKg / meses).toFixed(1) + " kg");
        safeSet("val-semanal", Math.round(gramosSemanales) + " g");

        // APLICACIÓN DE TU FÓRMULA: [(Mantenimiento - Gramos Semanales) * 0.8]
        // Con piso de 800 cal
        let resultadoMeta = (mantenimiento - gramosSemanales) * 0.8;
        safeSet("val-meta-calorica", Math.round(Math.max(resultadoMeta, 800)) + " kcal");

    } else {
        // Si NO desea bajar de peso
        if (tablaObj) tablaObj.style.display = "none";
        safeSet('objetivo-bajar', 'No');
        safeSet('objetivo-perdida', "---");
        safeSet('objetivo-tiempo', "---");

        // En mantenimiento, la meta calórica es igual al balance calórico
        safeSet("val-meta-calorica", mantenimiento + " kcal");
    }
    // 4. --- RECOMENDACIONES NUTRICIONALES DINÁMICAS ---
    const dHta = Diagnosticos.hipertension(d);
    const dGlu = Diagnosticos.glucosa(d);
    const dLip = Diagnosticos.lipidos(d);
    const rAzucar = parseFloat(d.vasos_bebidas_azucaradas) || 0;

    // Lógica dinámica para Lácteos
    const lacteosValor = d['frecuencia-lacteos'] || d.frecuencia_lacteos || "";
    const recLacteosAuto = (lacteosValor === "3 veces al día o más")
        ? "Mantener el consumo de lácteos bajos en grasa"
        : "Aumentar el consumo de lácteos bajos en grasa a 3 por día";

    // Lógica dinámica para Carnes
    const carnesValor = d['frecuencia-carnes'] || d.frecuencia_carnes || "";
    const recCarnesAuto = (carnesValor === "3 o más veces a la semana")
        ? "Reducir el consumo de carnes rojas o procesadas"
        : "Mantén un bajo consumo de carnes rojas o procesadas";

    const recsNutri = {
        'val-rec-sodio': d.rec_sodio || (dHta.alt ? "Reducir el consumo de sal" : "Mantener una dieta baja en sal"),
        'val-rec-frutas': d.rec_frutas || (parseFloat(d.raciones_frutas) < 3 ? "Aumentar el consumo de frutas a 3 por día" : "Excelente consumo de frutas"),
        'val-rec-vegetales': d.rec_vegetales || (parseFloat(d.raciones_vegetales) < 4 ? "Aumenta el consumo de vegetales a 4 porciones/día" : "Mantener consumo de vegetales"),
        'val-rec-azucar': d.rec_azucar || (rAzucar >= 4 ? "Reducir el consumo de bebidas azucaradas" : "Mantener consumo bajo de bebidas azucaradas"),
        'val-rec-grasas': d.rec_lipidos || (dLip.alt ? "Aumentar el consumo de grasas saludables" : "Mantener alimentación baja en grasas"),
        'val-rec-granos': d.rec_granos || (parseFloat(d.raciones_grano_entero) < 2 ? "Aumentar consumo de grano entero" : "Mantener consumo de grano entero"),
        'val-rec-pescado': d.rec_pescado || (parseFloat(d.raciones_pescado) < 2 ? "Aumentar consumo de pescado a 2 porciones/semana" : "Mantener consumo de pescado"),

        // Usamos la lógica que acabamos de crear
        'val-rec-lacteos': d.rec_lacteos || recLacteosAuto,

        'val-rec-carnes': d.rec_carnes || recCarnesAuto,
        'val-rec-alcohol': d.rec_alcohol || (d.frecuencia_alcohol?.includes("4 o más") ? "Reducir consumo de alcohol" : "Mantener consumo moderado/nulo")
    };

    for (const [id, val] of Object.entries(recsNutri)) { safeSet(id, val); }
    safeSet("val-diag-dislipidemia", dLip.label);

    // Actividad Física basada en Nivel
    const nivelParaRec = d['nivel-actividad'] || d.nivel_actividad || "";
    let recAct;

    switch (nivelParaRec) {
        case "Poco Activo":
            recAct = "Iniciar caminatas de 15-20 min diarios";
            break;
        case "Moderadamente Activo":
            recAct = "Aumentar intensidad o añadir 2 días de fuerza";
            break;
        case "Muy Activo":
            recAct = "Excelente, mantener ritmo y asegurar recuperación";
            break;
        default:
            recAct = "Establecer rutina de 150 min de actividad semanal";
    }

    safeSet("val-rec-actividad", d.rec_actividad || recAct);
    // --- SALUD MENTAL (Segmento 17) ---
    const ansScore = (rToS(d.ansiedad_nervios) + rToS(d.control_preocupacion)) || 0;
    const depScore = (rToS(d.poco_interes) + rToS(d.sentimiento_deprimido)) || 0;
    const optScore = parseInt(d.nivel_optimismo) || 0;
    const pesScore = parseInt(d.nivel_pesimismo) || 0;

    const recsMental = {
        'val-rec-ansiedad': d.rec_ansiedad || (ansScore >= 3
            ? "Incorpora rutinas de reducción de estrés y ansiedad (respiración, actividad física suave). Considera evaluación médica."
            : "Mantén actividades saludables que te protejan de la ansiedad."),

        'val-rec-depresion': d.rec_depresion || (depScore >= 3
            ? "Fomenta contacto social y movimiento físico para mejorar la energía. Considera evaluación médica."
            : "Mantén actividades saludables que te protejan de la depresión."),

        'val-rec-optimismo': d.rec_optimismo || (optScore < 5
            ? "Promueve una actitud orientada a resultados positivos."
            : "Mantén una actitud optimista."),

        'val-rec-pesimismo': d.rec_pesimismo || (pesScore > 3
            ? "Fomenta la reducción de patrones negativos persistentes."
            : "Mantén una actitud libre de pesimismo.")
    };

    // Aplicar recomendaciones de salud mental al DOM
    for (const [id, val] of Object.entries(recsMental)) {
        safeSet(id, val);
    }

    // Tabaco
    safeSet("val-rec-tabaco", d.rec_tabaco || (d.habito_tabaquico?.includes("fumo") ? "Plan médico de cesación (Parches/Terapia)" : "Mantener ambiente libre de humo"));
    // --- DENTRO DE LA LÓGICA DE RECOMENDACIONES DE CONDUCTA ---

    const esPasivo = d['exposicion-humo'] === "Sí, fuman en mi presencia";
    const recPasivoAuto = esPasivo
        ? "Evita ser fumador pasivo, manteniéndote en un ambiente libre de humo"
        : "Mantente en un ambiente libre de humo";

    safeSet("val-rec-pasivo", d.rec_pasivo || recPasivoAuto);
    // Apnea y Sueño
    const dApnea = Diagnosticos.apnea(d);
    safeSet("val-rec-apnea", d.rec_apnea || (dApnea.alt ? "Valoración por neumología (Posible CPAP)" : "Higiene de sueño: Dormir 7-8 horas"));

    // --- SALUD CARDIOVASCULAR (Segmento 18) ---
    let recPresionAuto = "";

    // Lógica de recomendación basada en el diagnóstico
    if (dHta.label === "Pendiente") {
        recPresionAuto = "Mide tus valores de presion arterial";
    }
    else if (
        dHta.label === "HTA No Controlada" ||
        dHta.label === "HTA No Controlada (Paciente con diabetes)" ||
        dHta.label === "HTA Controlada (No Optima)" ||
        dHta.label === "Hipertensión Controlada" || // Incluida por precaución según tu objeto
        dHta.label === "Presión Arterial Elevada"
    ) {
        recPresionAuto = "Puede ser necesario iniciar/ajustar la medicación para la presión arterial";
    }
    else {
        recPresionAuto = "Manten un adecuado control de tu presion arterial";
    }
    // Aplicar al DOM priorizando la recomendación manual del médico si existe
    safeSet("val-rec-presion", d.rec_presion || recPresionAuto);
    // --- SALUD CARDIOVASCULAR (Segmento 18) ---
    let recGlucosaAuto = "";

    // Lógica de recomendación basada en el label del diagnóstico de glucosa
    switch (dGlu.label) {
        case "Pendiente diagnóstico":
            recGlucosaAuto = "Mide tus valores de glucosa";
            break;
        case "Diabetes tratada no controlada":
            recGlucosaAuto = "Debes optimizar el tratamiento de la glucosa para evitar complicaciones";
            break;
        case "Diabetes tratada y controlada":
            recGlucosaAuto = "Manten tu tratamiento";
            break;
        case "Diabetes sin tratamiento":
            recGlucosaAuto = "Debes iniciar/ajustar tratamiento para optimizar tu nivel de glucosa";
            break;
        case "Prediabetes":
            recGlucosaAuto = "Inicia el programa de prevencion de diabetes";
            break;
        case "Normal":
            recGlucosaAuto = "Manten tu cuidado de glucosa";
            break;
        default:
            recGlucosaAuto = "Mantener equilibrio de macronutrientes";
    }

    // Aplicar al DOM priorizando la edición manual
    safeSet("val-rec-glucosa", d.rec_glucosa || recGlucosaAuto);

    // --- LÓGICA DE LÍPIDOS (Segmento 18) ---
    let recLipidosAuto = "";

    // Mapeo de recomendaciones según el label del diagnóstico
    switch (dLip.label) {
        case "Pendiente":
            recLipidosAuto = "Realiza un perfil lipídico completo (LDL, HDL y Triglicéridos)";
            break;
        case "Dislipidemia":
            recLipidosAuto = "Optimiza el consumo de grasas saludables y considera evaluación médica para tratamiento";
            break;
        case "Dislipidemia (Tratada)":
            recLipidosAuto = "Mantén tu tratamiento actual y monitorea niveles para asegurar metas de control";
            break;
        case "Normal (Tratada)":
            recLipidosAuto = "Excelente control bajo tratamiento; continúa con tus hábitos y medicación";
            break;
        case "Normal":
            recLipidosAuto = "Mantén una dieta balanceada para conservar niveles óptimos de colesterol";
            break;
        default:
            recLipidosAuto = "Mantener control anual de perfil lipídico";
    }

    // Aplicar al DOM
    // Nota: Usamos 'val-rec-lipidos-cardio' para que coincida con el ID de tu HTML anterior
    safeSet("val-rec-lipidos-cardio", d.rec_lipidos_cardio || recLipidosAuto);
}


/**
 * ============================================================
 * 13. EXPORTACIÓN, GUARDADO Y UTILIDADES DE SISTEMA
 * ============================================================
 */

/**
 * Carga la lista de participantes en el selector del sidebar
 */
async function cargarParticipantesEnSelector(selectEl, currentId) {
    try {
        const response = await fetch('/api/all_participants');
        if (!response.ok) return;
        const participantes = await response.json();

        // Si el selector ya tiene opciones (por Jinja), no lo sobreescribimos por completo
        // pero aseguramos que el valor actual esté seleccionado
        if (selectEl.options.length <= 1 && participantes.length > 0) {
            selectEl.innerHTML = '<option value="">-- Seleccione un participante --</option>' +
                participantes.map(p => `<option value="${p.id}" ${p.id == currentId ? 'selected' : ''}>${p.nombre_completo}</option>`).join('');
        }
    } catch (e) {
        console.warn("No se pudieron cargar los participantes adicionales:", e);
    }
}

/**
 * Obtiene el ID del envío desde múltiples fuentes (URL, Path, Global)
 */
function getSubmissionId() {
    // 1. Intentar desde parámetros de URL (?id=...)
    const urlParams = new URLSearchParams(window.location.search);
    let id = urlParams.get('id') || urlParams.get('submission');

    // 2. Intentar desde el path de la URL (/reporte/123)
    if (!id) {
        const pathSegments = window.location.pathname.split('/');
        const lastSegment = pathSegments[pathSegments.length - 1];
        if (!isNaN(lastSegment) && lastSegment !== '') id = lastSegment;
    }

    // 3. Fallback: buscar en el texto del elemento 'paciente-id'
    if (!id) {
        const el = document.getElementById('paciente-id');
        if (el) id = el.innerText.replace(/\D/g, '');
    }

    return (id && id !== 'undefined') ? id : "ID_DESCONOCIDO";
}

/**
 * Genera un archivo .txt con la totalidad de los datos del paciente (18 segmentos)
 */
function descargarReporteTxtParaGemini() {
    const id = getSubmissionId();
    const ahora = new Date();
    const fechaStr = ahora.toLocaleDateString() + ' ' + ahora.toLocaleTimeString();

    // Helper para extraer texto de la UI (post-edición o cálculo)
    const getVal = (id) => {
        const el = document.getElementById(id);
        if (!el) return '--';
        let val = el.innerText.trim() || el.value || '--';
        return val;
    };

    // Helper para Antecedentes (Colecciona todos los que digan "Presente")
    const getAntecedentes = () => {
        const rows = document.querySelectorAll('#lista-antecedentes tr');
        const present = [];
        rows.forEach(row => {
            const label = row.cells[0]?.innerText.trim();
            const status = row.cells[1]?.innerText.trim();
            if (status === 'Presente') present.push(label);
        });
        return present.length > 0 ? present.join(', ') : 'No se registraron antecedentes';
    };

    // Helper para Complicaciones (Detectar cuáles están marcadas como DETECTADO)
    const getComplicaciones = () => {
        const cards = document.querySelectorAll('#grid-complicaciones > div');
        const detected = [];
        cards.forEach(card => {
            const label = card.querySelector('p:first-child')?.innerText.trim();
            const status = card.querySelector('p:last-child')?.innerText.trim();
            if (status === 'DETECTADO') detected.push(label);
        });
        return detected.length > 0 ? detected.join(', ') : 'Ninguna complicación detectada';
    };

    let contenido = `==================================================\n`;
    contenido += `       REPORTE MÉDICO INTEGRAL DE SALUD\n`;
    contenido += `==================================================\n\n`;

    contenido += `00. IDENTIFICACIÓN Y METADATOS:\n`;
    contenido += `- ID Seguimiento: ${id}\n`;
    contenido += `- Fecha de Reporte: ${fechaStr}\n`;
    contenido += `- Nombre: ${getVal('p-nombre')} ${getVal('p-apellidos')}\n`;

    let edad = getVal('p-edad');
    if (!edad.includes('años')) edad += ' años';
    contenido += `- Edad: ${edad}\n`;

    contenido += `- Género: ${getVal('p-sexo')}\n\n`;

    contenido += `01. ESTADO ANTROPOMÉTRICO:\n`;
    contenido += `- Peso: ${getVal('p-peso')} kg | Talla: ${getVal('p-talla')} cm\n`;
    contenido += `- IMC: ${getVal('imc-gauge-val')} (${getVal('imc-gauge-label')})\n`;
    contenido += `- Perímetro Abdominal: ${getVal('abd-gauge-val')} cm (${getVal('abd-gauge-label')})\n\n`;

    contenido += `02. LABORATORIO - PERFIL GLUCÉMICO:\n`;
    contenido += `- Diagnóstico Glucosa: ${getVal('diag-glucosa')}\n`;
    contenido += `- Glucosa en ayunas: ${getVal('p-glucosa')} mg/dL\n`;
    contenido += `- Hemoglobina Glicosilada (HbA1c): ${getVal('p-hba1c')}%\n`;
    contenido += `- Toma medicación para glucosa: ${getVal('h-med-glucosa')}\n`;
    contenido += `- Recomendación: ${getVal('val-rec-glucosa')}\n\n`;

    contenido += `03. LABORATORIO - PERFIL HEMODINÁMICO:\n`;
    contenido += `- Diagnóstico Presión: ${getVal('diag-presion')}\n`;
    contenido += `- Presión Sistólica: ${getVal('p-presion-sistolica')} mmHg\n`;
    contenido += `- Presión Diastólica: ${getVal('p-presion-diastolica')} mmHg\n`;
    contenido += `- Toma medicación para presión: ${getVal('h-med-presion')}\n`;
    contenido += `- Recomendación: ${getVal('val-rec-presion')}\n\n`;

    contenido += `04. LABORATORIO - PERFIL LIPÍDICO:\n`;
    contenido += `- Diagnóstico Lípidos: ${getVal('diag-lipidos')}\n`;
    contenido += `- Colesterol Total: ${getVal('p-col-total')} mg/dL\n`;
    contenido += `- Colesterol LDL: ${getVal('p-col-ldl')} mg/dL\n`;
    contenido += `- Colesterol HDL: ${getVal('p-col-hdl')} mg/dL\n`;
    contenido += `- Triglicéridos: ${getVal('p-trigliceridos')} mg/dL\n`;
    contenido += `- Toma medicación para lípidos: ${getVal('h-med-lipidos')}\n`;
    contenido += `- Recomendación: ${getVal('val-rec-lipidos-cardio')}\n\n`;

    contenido += `05. SALUD MENTAL Y BIENESTAR:\n`;
    contenido += `- Ansiedad (Score): ${getVal('val-m-ans')} | Diagnóstico: ${getVal('res-ansiedad')}\n`;
    contenido += `- Depresión (Score): ${getVal('val-m-dep')} | Diagnóstico: ${getVal('res-depresion')}\n`;
    contenido += `- Optimismo: ${getVal('val-m-opt')} | Pesimismo: ${getVal('val-m-pes')}\n`;
    contenido += `- Calidad de Vida: ${getVal('val-m-qol')}/100\n`;
    contenido += `- Rec. Ansiedad: ${getVal('val-rec-ansiedad')}\n`;
    contenido += `- Rec. Depresión: ${getVal('val-rec-depresion')}\n`;
    contenido += `- Rec. Optimismo/Pesimismo: ${getVal('val-rec-optimismo')} / ${getVal('val-rec-pesimismo')}\n\n`;

    contenido += `06. ANTECEDENTES Y RIESGO BIOLÓGICO:\n`;
    contenido += `- Riesgo Familiar/Biológico: ${getVal('res-riesgo-bio')}\n`;
    contenido += `- Antecedentes detallados: ${getAntecedentes()}\n\n`;

    contenido += `07. HÁBITOS DE VIDA Y CONDUCTA:\n`;
    contenido += `- Tabaquismo (Activo): ${getVal('res-tabaquismo')}\n`;
    contenido += `- Fumador Pasivo: ${getVal('res-fumador-pasivo')}\n`;
    contenido += `- Consumo Alcohol: ${getVal('h-alcohol')} (${getVal('h-alcohol-cant')} bebidas/día)\n`;
    contenido += `- Nivel Actividad Física: ${getVal('h-nivel-actividad')} (${getVal('res-actividad-nivel')})\n`;
    contenido += `- Rec. Actividad Física: ${getVal('val-rec-actividad')}\n\n`;

    contenido += `08. SUEÑO Y RIESGO RESPIRATORIO:\n`;
    contenido += `- Calidad de Sueño: ${getVal('res-sueno')}\n`;
    contenido += `- Riesgo de Apnea (STOP-BANG): ${getVal('res-apnea')}\n`;
    contenido += `- Recomendación Sueño/Apnea: ${getVal('val-rec-apnea')}\n\n`;

    contenido += `09. NUTRICIÓN DETALLADA:\n`;
    contenido += `- Puntaje Dieta: ${getVal('val-puntaje-alim')}/6\n`;
    contenido += `- Consumo Frutas: ${getVal('h-frutas')} | Vegetales: ${getVal('h-vegetales')}\n`;
    contenido += `- Pescado: ${getVal('h-pescado')} | Granos: ${getVal('h-granos')}\n`;
    contenido += `- Sodio/Sal: ${getVal('h-sal')} | Azúcar/Bebidas: ${getVal('h-azucar')}\n`;
    contenido += `- Recomendación General: ${getVal('val-rec-grasas')}\n\n`;

    contenido += `10. RECOMENDACIONES NUTRICIONALES ESPECÍFICAS:\n`;
    contenido += `- Grasas: ${getVal('val-rec-grasas')}\n`;
    contenido += `- Sodio: ${getVal('val-rec-sodio')}\n`;
    contenido += `- Frutas: ${getVal('val-rec-frutas')}\n`;
    contenido += `- Vegetales: ${getVal('val-rec-vegetales')}\n`;
    contenido += `- Granos Enteros: ${getVal('val-rec-granos')}\n`;
    contenido += `- Proteínas (Pescado): ${getVal('val-rec-pescado')}\n`;
    contenido += `- Bebidas Azucaradas: ${getVal('val-rec-azucar')}\n`;
    contenido += `- Carnes Rojas: ${getVal('val-rec-carnes')}\n`;
    contenido += `- Lácteos: ${getVal('val-rec-lacteos')}\n`;
    contenido += `- Consumo de Alcohol: ${getVal('val-rec-alcohol')}\n\n`;

    contenido += `11. BALANCE ENERGÉTICO:\n`;
    contenido += `- Tasa Metabólica Basal (TMB): ${getVal('mb-peso')}\n`;
    contenido += `- Gasto Energético Total: ${getVal('val-balance-calorico')}\n`;
    contenido += `- Meta Calórica Recomendada: ${getVal('val-meta-calorica')}\n\n`;

    contenido += `12. MANEJO DEL PESO (DETALLADO):\n`;
    contenido += `- Recomendación General: ${getVal('val-rec-peso')}\n`;
    contenido += `- Metabolismo Basal: ${getVal('mb-peso')}\n`;
    contenido += `- Balance Calórico 24h: ${getVal('val-balance-calorico')}\n`;
    contenido += `- ¿Desea bajar de peso?: ${getVal('objetivo-bajar')}\n`;
    contenido += `- Cuanto desea perder: ${getVal('objetivo-perdida')}\n`;
    contenido += `- En cuanto tiempo: ${getVal('objetivo-tiempo')}\n`;

    // Solo incluir tabla de objetivos si desea bajar de peso
    if (getVal('objetivo-bajar').toLowerCase() === 'sí') {
        contenido += `   --- Metas de Peso ---\n`;
        contenido += `   - Peso Actual: ${getVal('val-peso-actual')}\n`;
        contenido += `   - Peso a Alcanzar: ${getVal('val-peso-meta')}\n`;
        contenido += `   - Reducir en kg: ${getVal('val-peso-reducir')}\n`;
        contenido += `   - Tiempo (Meses): ${getVal('val-meses')}\n`;
        contenido += `   - Objetivo Mensual: ${getVal('val-mensual')}\n`;
        contenido += `   - Objetivo Semanal: ${getVal('val-semanal')}\n`;
    }
    contenido += `- Meta Calórica Final: ${getVal('val-meta-calorica')}\n\n`;

    contenido += `13. OTROS HALLAZGOS Y RECOMENDACIONES:\n`;
    contenido += `- Tabaquismo/Ambiente: ${getVal('val-rec-tabaco')}\n`;
    contenido += `- Entorno Familiar/Pasivo: ${getVal('val-rec-pasivo')}\n`;
    contenido += `- AHA Life's Essential Score: ${getVal('val-aha-total')}/100\n\n`;

    contenido += `14. COMPLICACIONES Y HALLAZGOS CRÍTICOS:\n`;
    contenido += `- Complicaciones Detectadas: ${getComplicaciones()}\n`;

    contenido += `\n==================================================\n`;
    contenido += `       FIN DEL REPORTE MÉDICO\n`;
    contenido += `==================================================`;

    // Disparar descarga
    const blob = new Blob([contenido], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Reporte_Salud_Completo_${getVal('p-nombre') || id}.txt`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
}
/**
 * Evento para guardar cambios en la base de datos (POST)
 * Incluye el análisis pegado de Gemini y todos los campos editables.
 * Se ha eliminado la recarga de página para mantener el texto visible.
 */
const btnGuardar = document.getElementById('btn-guardar-cambios');

if (btnGuardar) {
    btnGuardar.addEventListener('click', async function () {
        const btn = this;
        const originalHTML = btn.innerHTML;

        // Estado visual de carga
        btn.innerHTML = `<span class="animate-spin inline-block mr-2">↻</span> Guardando...`;
        btn.disabled = true;

        const dataToSave = {
            id: getSubmissionId(),
            fecha_actualizacion: new Date().toISOString()
        };

        // RECOLECCIÓN DINÁMICA: 
        // Captura IMC, Presión, Recomendaciones y el Análisis de Gemini (analisis_driver)
        document.querySelectorAll('[data-key]').forEach(el => {
            const key = el.getAttribute('data-key');
            if (key) {
                // Si el campo tiene el texto inicial por defecto, lo enviamos vacío o tratamos el texto
                let valor = el.innerText.trim();
                if (valor === "Cargando análisis personalizado...") {
                    valor = "";
                }
                dataToSave[key] = valor;
            }
        });

        try {
            const response = await fetch('/update_submission', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(dataToSave)
            });

            const result = await response.json();

            if (response.ok) {
                mostrarNotificacion("✓ Reporte y análisis guardados con éxito", "success");

                // IMPORTANTE: Se elimina location.reload() para que el resumen pegado 
                // permanezca visible en la pantalla sin interrupciones.
                console.log("Cambios sincronizados con la base de datos.");
            } else {
                throw new Error(result.message || "Error en el servidor");
            }
        } catch (error) {
            console.error("Error al guardar:", error);
            mostrarNotificacion("❌ Error: No se pudo conectar con el servidor", "error");
        } finally {
            btn.innerHTML = originalHTML;
            btn.disabled = false;
        }
    });
}

/**
 * Gestión del área de texto del Coach Virtual
 * Limpia el mensaje por defecto al hacer foco para facilitar el pegado.
 */
const narrativaDiv = document.getElementById('narrativa-ia');
if (narrativaDiv) {
    narrativaDiv.addEventListener('focus', function () {
        if (this.innerText.trim() === 'Cargando análisis personalizado...') {
            this.innerText = '';
        }
    });

    // Opcional: Si se desenfoca y está vacío, restaurar el mensaje (ayuda visual)
    narrativaDiv.addEventListener('blur', function () {
        if (this.innerText.trim() === '') {
            this.innerText = 'Cargando análisis personalizado...';
        }
    });
}

/**
 * UI Helper: Notificaciones flotantes
 */
function mostrarNotificacion(msg, tipo) {
    const box = document.createElement('div');
    const color = tipo === 'success' ? '#10b981' : '#ef4444';
    box.style = `
        position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
        background: ${color}; color: white; padding: 12px 24px;
        border-radius: 50px; z-index: 10000; font-weight: bold;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3); animation: slideUp 0.3s ease;
    `;
    box.innerText = msg;
    document.body.appendChild(box);
    setTimeout(() => {
        box.style.opacity = '0';
        box.style.transition = '0.5s';
        setTimeout(() => box.remove(), 500);
    }, 3000);
}