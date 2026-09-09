"""
Benchmark clínico — Fase 12.

Recomendación externa (prioridad 1): "Es lo único que te da un número
verificable. Sin eso, 'suena bien' pero no se puede medir."

Este script le hace al modelo un set de preguntas de opción múltiple
estilo ENARM/USMLE (escritas por Claude para este propósito — NO son
preguntas reales de ningún examen, por derechos de autor; están
calibradas al mismo nivel de dificultad y formato: viñeta clínica +
4 opciones + una sola respuesta correcta) y mide qué porcentaje
contesta bien. Es el "número verificable" que la recomendación pide.

No es parte de la app en sí — es una herramienta de evaluación aparte,
pensada para correr de vez en cuando (ej. después de cambiar el
SYSTEM_PROMPT o el modelo) y ver si la precisión sube o baja, no algo
que el estudiante vea nunca.

CÓMO CORRERLO:
    python benchmark_medico.py
Necesita las mismas variables de entorno que la app (GROQ_API_KEY vía
.env o el entorno) — usa config.py tal cual, así que corre esto desde
la misma carpeta que el resto de los módulos del proyecto.

Qué imprime al final:
  - Precisión global (% de aciertos)
  - Precisión por especialidad
  - La lista de preguntas falladas, con la respuesta que dio el modelo
    y la correcta, para que puedas revisar el patrón de error (esto es
    justo el insumo que después complementa con el dataset de 👎 de
    feedback.py — dos fuentes de error distintas: preguntas "de examen"
    controladas aquí, y preguntas reales de estudiantes allá).
"""
import re
import sys
import time

from config import client, MODELO_CHAT

PREGUNTAS = [
    {
        "especialidad": "Cardiología",
        "pregunta": (
            "Hombre de 58 años acude por dolor torácico opresivo de 2 horas de evolución, "
            "irradiado a brazo izquierdo, con diaforesis y náusea. ECG muestra elevación del "
            "segmento ST en derivaciones II, III y aVF. ¿Cuál es el diagnóstico más probable?"
        ),
        "opciones": [
            "Infarto agudo de miocardio de cara inferior",
            "Infarto agudo de miocardio de cara anterior",
            "Pericarditis aguda",
            "Disección aórtica tipo A",
        ],
        "respuesta_correcta": 0,
        "explicacion": "Las derivaciones II, III y aVF corresponden a la cara inferior (irrigada por la coronaria derecha en la mayoría de los pacientes).",
    },
    {
        "especialidad": "Endocrinología",
        "pregunta": (
            "Mujer de 34 años con hipertensión resistente, hipopotasemia e hipernatremia leve. "
            "Aldosterona plasmática elevada con renina suprimida. ¿Cuál es el diagnóstico más probable?"
        ),
        "opciones": [
            "Feocromocitoma",
            "Hiperaldosteronismo primario",
            "Síndrome de Cushing",
            "Estenosis de la arteria renal",
        ],
        "respuesta_correcta": 1,
        "explicacion": "Aldosterona alta + renina suprimida (relación aldosterona/renina elevada) es el patrón clásico de hiperaldosteronismo primario, no secundario.",
    },
    {
        "especialidad": "Enfermedades infecciosas",
        "pregunta": (
            "Paciente de 24 años con fiebre, cefalea intensa, rigidez de nuca y fotofobia de "
            "12 horas de evolución. La punción lumbar muestra líquido turbio, glucosa baja, "
            "proteínas elevadas y predominio de polimorfonucleares. ¿Cuál es la conducta inicial más adecuada?"
        ),
        "opciones": [
            "Esperar el cultivo de LCR antes de iniciar tratamiento",
            "Iniciar antibiótico empírico de inmediato, sin esperar resultados de cultivo",
            "Iniciar tratamiento antiviral empírico",
            "Dar analgésicos y observar 24 horas",
        ],
        "respuesta_correcta": 1,
        "explicacion": "El patrón de LCR sugiere meningitis bacteriana — es una emergencia médica, el antibiótico empírico no debe retrasarse por el cultivo.",
    },
    {
        "especialidad": "Nefrología",
        "pregunta": (
            "Hombre de 45 años con antecedente de diabetes tipo 2, creatinina sérica 2.1 mg/dL, "
            "peso 80 kg, sin edema significativo, requiere ajuste de dosis de un antibiótico de "
            "eliminación renal. ¿Qué fórmula es la más apropiada para estimar su función renal "
            "con este propósito?"
        ),
        "opciones": [
            "CKD-EPI",
            "Cockcroft-Gault",
            "MDRD",
            "Fórmula de Schwartz",
        ],
        "respuesta_correcta": 1,
        "explicacion": "Cockcroft-Gault sigue siendo la fórmula estándar para AJUSTAR DOSIS de fármacos; CKD-EPI/MDRD son para estadificar ERC, no para dosificación. Schwartz es pediátrica.",
    },
    {
        "especialidad": "Psiquiatría",
        "pregunta": (
            "Paciente que inicia tratamiento con un IMAO consume queso curado y desarrolla "
            "cefalea intensa súbita, hipertensión severa y taquicardia. ¿Cuál es el mecanismo "
            "más probable de esta reacción?"
        ),
        "opciones": [
            "Síndrome serotoninérgico",
            "Crisis hipertensiva por tiramina",
            "Síndrome neuroléptico maligno",
            "Reacción anafiláctica",
        ],
        "respuesta_correcta": 1,
        "explicacion": "Los IMAO bloquean el metabolismo de la tiramina; alimentos ricos en tiramina (quesos curados) pueden precipitar una crisis hipertensiva.",
    },
    {
        "especialidad": "Neumología",
        "pregunta": (
            "Mujer de 68 años, fumadora, con disnea progresiva, tos productiva crónica y "
            "espirometría con relación FEV1/FVC < 0.70 que no mejora significativamente con "
            "broncodilatador. ¿Cuál es el diagnóstico más probable?"
        ),
        "opciones": [
            "Asma bronquial",
            "Enfermedad pulmonar obstructiva crónica",
            "Fibrosis pulmonar idiopática",
            "Bronquiectasias",
        ],
        "respuesta_correcta": 1,
        "explicacion": "Patrón obstructivo NO reversible con broncodilatador en fumadora crónica es el cuadro clásico de EPOC, a diferencia del asma (reversible).",
    },
    {
        "especialidad": "Gastroenterología",
        "pregunta": (
            "Hombre de 50 años con hematemesis, antecedente de cirrosis hepática conocida. "
            "A la exploración: hipotensión, taquicardia, y datos de hipertensión portal. "
            "¿Cuál es la causa más probable del sangrado?"
        ),
        "opciones": [
            "Úlcera péptica",
            "Várices esofágicas",
            "Síndrome de Mallory-Weiss",
            "Gastritis erosiva",
        ],
        "respuesta_correcta": 1,
        "explicacion": "En un paciente cirrótico con hipertensión portal conocida, las várices esofágicas son la causa más probable de hemorragia digestiva alta.",
    },
    {
        "especialidad": "Hematología",
        "pregunta": (
            "Paciente con anemia microcítica hipocrómica, ferritina baja, hierro sérico bajo y "
            "capacidad de fijación de hierro (TIBC) elevada. ¿Cuál es el diagnóstico más probable?"
        ),
        "opciones": [
            "Anemia de enfermedad crónica",
            "Anemia ferropénica",
            "Talasemia menor",
            "Anemia sideroblástica",
        ],
        "respuesta_correcta": 1,
        "explicacion": "Ferritina baja + TIBC alta es el patrón distintivo de deficiencia real de hierro; en anemia de enfermedad crónica la ferritina suele estar normal o alta.",
    },
    {
        "especialidad": "Neurología",
        "pregunta": (
            "Mujer de 72 años presenta debilidad facial derecha, disartria y debilidad en brazo "
            "derecho de inicio súbito hace 90 minutos. Tomografía de cráneo sin contraste no "
            "muestra hemorragia. ¿Cuál es la conducta terapéutica más urgente a evaluar?"
        ),
        "opciones": [
            "Iniciar anticoagulación con heparina de inmediato",
            "Evaluar elegibilidad para trombólisis intravenosa",
            "Solicitar resonancia magnética antes de cualquier tratamiento",
            "Iniciar aspirina en dosis altas de inmediato",
        ],
        "respuesta_correcta": 1,
        "explicacion": "Con TC sin hemorragia y dentro de la ventana de tiempo, evaluar trombólisis IV es la prioridad en un probable EVC isquémico agudo.",
    },
    {
        "especialidad": "Reumatología",
        "pregunta": (
            "Mujer de 28 años con artralgias simétricas de pequeñas articulaciones, eritema "
            "malar que respeta el surco nasolabial, fotosensibilidad, y anticuerpos "
            "antinucleares positivos a título alto. ¿Cuál es el diagnóstico más probable?"
        ),
        "opciones": [
            "Artritis reumatoide",
            "Lupus eritematoso sistémico",
            "Dermatomiositis",
            "Esclerosis sistémica",
        ],
        "respuesta_correcta": 1,
        "explicacion": "Eritema malar + fotosensibilidad + ANA positivo a título alto en mujer joven es el cuadro clásico de LES.",
    },
    {
        "especialidad": "Farmacología",
        "pregunta": (
            "Paciente en tratamiento con warfarina inicia un antibiótico macrólido para una "
            "infección respiratoria. ¿Cuál es el efecto esperado sobre el INR?"
        ),
        "opciones": [
            "El INR disminuye, requiere aumentar la dosis de warfarina",
            "El INR aumenta, requiere vigilancia estrecha por riesgo de sangrado",
            "No hay interacción clínicamente relevante",
            "El macrólido inactiva a la warfarina por completo",
        ],
        "respuesta_correcta": 1,
        "explicacion": "Los macrólidos inhiben el metabolismo de warfarina (CYP3A4), aumentando su efecto anticoagulante y el riesgo de sangrado.",
    },
    {
        "especialidad": "Ginecología y obstetricia",
        "pregunta": (
            "Mujer embarazada de 26 semanas presenta presión arterial de 150/95 mmHg en dos "
            "tomas separadas, sin proteinuria, sin cefalea ni alteraciones visuales. ¿Cuál es "
            "el diagnóstico más probable?"
        ),
        "opciones": [
            "Preeclampsia",
            "Hipertensión gestacional",
            "Hipertensión crónica",
            "Eclampsia",
        ],
        "respuesta_correcta": 1,
        "explicacion": "Hipertensión de novo después de la semana 20 SIN proteinuria ni datos de severidad se clasifica como hipertensión gestacional, no preeclampsia.",
    },
    {
        "especialidad": "Pediatría",
        "pregunta": (
            "Lactante de 6 meses presenta tos paroxística seguida de un 'estridor inspiratorio' "
            "característico y episodios de cianosis, sin fiebre significativa. No tiene esquema "
            "de vacunación completo. ¿Cuál es el diagnóstico más probable?"
        ),
        "opciones": [
            "Bronquiolitis por virus sincitial respiratorio",
            "Tos ferina (pertussis)",
            "Crup viral",
            "Cuerpo extraño en vía aérea",
        ],
        "respuesta_correcta": 1,
        "explicacion": "El estridor inspiratorio característico ('gallo') tras accesos de tos, en lactante no vacunado, es el cuadro clásico de tos ferina.",
    },
    {
        "especialidad": "Dermatología",
        "pregunta": (
            "Paciente con placas eritemato-descamativas bien delimitadas en superficies "
            "extensoras (codos, rodillas), con signo de Auspitz positivo al desprender la "
            "escama. ¿Cuál es el diagnóstico más probable?"
        ),
        "opciones": [
            "Dermatitis atópica",
            "Psoriasis en placas",
            "Pitiriasis rosada",
            "Tiña corporis",
        ],
        "respuesta_correcta": 1,
        "explicacion": "Placas bien delimitadas en superficies extensoras + signo de Auspitz (sangrado puntiforme al desprender la escama) son característicos de psoriasis.",
    },
    {
        "especialidad": "Endocrinología",
        "pregunta": (
            "Paciente con debilidad muscular proximal, hipotensión, hiperpigmentación cutánea "
            "difusa e hiperpigmentación de mucosas. Sodio bajo, potasio elevado. ¿Cuál es el "
            "diagnóstico más probable?"
        ),
        "opciones": [
            "Síndrome de Cushing",
            "Insuficiencia suprarrenal primaria (enfermedad de Addison)",
            "Hipotiroidismo",
            "Enfermedad renal crónica",
        ],
        "respuesta_correcta": 1,
        "explicacion": "Hiperpigmentación mucocutánea (por ACTH elevada) + hiponatremia + hiperpotasemia es el patrón clásico de insuficiencia suprarrenal primaria.",
    },
]


def _extraer_letra_respuesta(texto_modelo: str):
    """
    Busca la letra/número de la opción elegida en la respuesta del
    modelo. Tolerante a variaciones ('A', 'a)', 'Opción A', '1', etc.).
    Devuelve el índice (0-3) o None si no se pudo identificar con
    confianza — mejor no adivinar que contar un acierto/fallo dudoso.
    """
    texto_modelo = texto_modelo.strip()
    m = re.search(r"\b([A-Da-d])\b", texto_modelo[:20])
    if m:
        return "abcd".index(m.group(1).lower())
    m = re.search(r"\b([1-4])\b", texto_modelo[:20])
    if m:
        return int(m.group(1)) - 1
    return None


def preguntar_al_modelo(pregunta: dict) -> str:
    """Le manda la viñeta + opciones al modelo tal como lo haría el
    chat real, pidiéndole SOLO la letra de la respuesta (para poder
    parsear de forma confiable) — temperature=0 para reproducibilidad
    entre corridas del benchmark."""
    letras = ["A", "B", "C", "D"]
    opciones_texto = "\n".join(f"{letras[i]}) {op}" for i, op in enumerate(pregunta["opciones"]))
    prompt = (
        f"{pregunta['pregunta']}\n\n{opciones_texto}\n\n"
        "Responde ÚNICAMENTE con la letra de la opción correcta (A, B, C o D), "
        "sin explicación, sin texto adicional."
    )
    respuesta = client.chat.completions.create(
        model=MODELO_CHAT,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0,
    )
    return respuesta.choices[0].message.content or ""


def correr_benchmark():
    if not client:
        print("❌ El cliente de Groq no está configurado (falta GROQ_API_KEY). No se puede correr el benchmark.")
        sys.exit(1)

    print("=" * 70)
    print(f"BENCHMARK CLÍNICO — {len(PREGUNTAS)} preguntas, modelo: {MODELO_CHAT}")
    print("=" * 70)
    print()

    resultados = []
    for i, p in enumerate(PREGUNTAS, start=1):
        try:
            texto_respuesta = preguntar_al_modelo(p)
            indice_elegido = _extraer_letra_respuesta(texto_respuesta)
        except Exception as ex:
            texto_respuesta = f"[ERROR: {ex}]"
            indice_elegido = None

        acierto = indice_elegido == p["respuesta_correcta"]
        resultados.append({**p, "respuesta_modelo_cruda": texto_respuesta,
                            "indice_elegido": indice_elegido, "acierto": acierto})

        marca = "✅" if acierto else ("❔" if indice_elegido is None else "❌")
        print(f"{marca} [{i:02d}/{len(PREGUNTAS)}] {p['especialidad']}")
        time.sleep(0.3)

    print()
    print("=" * 70)
    print("RESULTADOS")
    print("=" * 70)

    total = len(resultados)
    aciertos = sum(1 for r in resultados if r["acierto"])
    print(f"\nPrecisión global: {aciertos}/{total} ({aciertos/total*100:.1f}%)\n")

    por_especialidad = {}
    for r in resultados:
        d = por_especialidad.setdefault(r["especialidad"], {"aciertos": 0, "total": 0})
        d["total"] += 1
        d["aciertos"] += 1 if r["acierto"] else 0

    print("Por especialidad:")
    for esp, d in sorted(por_especialidad.items()):
        print(f"  {esp}: {d['aciertos']}/{d['total']} ({d['aciertos']/d['total']*100:.0f}%)")

    fallidas = [r for r in resultados if not r["acierto"]]
    if fallidas:
        print()
        print("=" * 70)
        print(f"PREGUNTAS FALLADAS O NO IDENTIFICADAS ({len(fallidas)}) — para revisar patrones:")
        print("=" * 70)
        letras = ["A", "B", "C", "D"]
        for r in fallidas:
            correcta = letras[r["respuesta_correcta"]]
            elegida = letras[r["indice_elegido"]] if r["indice_elegido"] is not None else "?"
            print(f"\n[{r['especialidad']}] {r['pregunta'][:100]}...")
            print(f"  Correcta: {correcta} | Modelo eligió: {elegida} (respuesta cruda: {r['respuesta_modelo_cruda']!r})")
            print(f"  Por qué: {r['explicacion']}")
    else:
        print("\n🎉 El modelo acertó todas las preguntas del benchmark.")

    return {"total": total, "aciertos": aciertos, "por_especialidad": por_especialidad, "fallidas": fallidas}


if __name__ == "__main__":
    correr_benchmark()
