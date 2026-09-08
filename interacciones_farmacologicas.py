"""
Verificador de interacciones farmacológicas (Fase 5).

Dos niveles, siguiendo el mismo principio que citas_evidencia.py aplica
al resto de la app — separar "evidencia curada verificable" de
"conocimiento general del modelo":

1. Base de datos local curada a mano (BASE_INTERACCIONES) — interacciones
   clásicas, ampliamente descritas en farmacología, con severidad,
   mecanismo y recomendación. Es deliberadamente pequeña y no pretende
   ser exhaustiva: es material de estudio, no un motor de verificación
   clínica completo (para eso existen herramientas como Lexicomp,
   Micromedex o UpToDate).

2. Respaldo por IA (analizar_interaccion_con_ia) — SOLO para el par que
   no está en la base local, y bajo pedido explícito del estudiante (la
   UI nunca lo llama automáticamente). Se etiqueta siempre como
   conocimiento general no verificado y nunca se mezcla visualmente con
   los resultados de la base curada.
"""
import unicodedata

from config import client, MODELO_AUXILIAR
from traducciones import t


def _normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = texto.strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


# Alias -> nombre canónico. Incluye genéricos, algunos nombres
# comerciales de uso frecuente en habla hispana, y clases terapéuticas
# completas cuando la interacción aplica a toda la clase (ej. "imao",
# "isrs", "macrolido") en vez de a un solo fármaco.
ALIAS_FARMACOS = {
    "acido acetilsalicilico": "aspirina", "asa": "aspirina", "aspirina": "aspirina",
    "paracetamol": "paracetamol", "acetaminofen": "paracetamol", "acetaminofeno": "paracetamol",
    "warfarina": "warfarina", "coumadin": "warfarina",
    "ibuprofeno": "ibuprofeno", "advil": "ibuprofeno",
    "naproxeno": "naproxeno",
    "diclofenaco": "diclofenaco",
    "omeprazol": "omeprazol",
    "clopidogrel": "clopidogrel", "plavix": "clopidogrel",
    "metformina": "metformina",
    "sildenafilo": "sildenafilo", "viagra": "sildenafilo", "tadalafilo": "sildenafilo",
    "nitroglicerina": "nitratos", "isosorbide": "nitratos", "dinitrato de isosorbide": "nitratos",
    "simvastatina": "estatina", "atorvastatina": "estatina", "lovastatina": "estatina", "rosuvastatina": "estatina",
    "claritromicina": "macrolido", "eritromicina": "macrolido", "azitromicina": "macrolido",
    "fluoxetina": "isrs", "sertralina": "isrs", "paroxetina": "isrs", "citalopram": "isrs", "escitalopram": "isrs",
    "tramadol": "tramadol",
    "fenelzina": "imao", "tranilcipromina": "imao", "selegilina": "imao", "moclobemida": "imao",
    "digoxina": "digoxina",
    "amiodarona": "amiodarona",
    "espironolactona": "ahorrador de potasio", "amilorida": "ahorrador de potasio", "eplerenona": "ahorrador de potasio",
    "enalapril": "ieca", "lisinopril": "ieca", "captopril": "ieca", "ramipril": "ieca",
    "losartan": "ara2", "valsartan": "ara2", "irbesartan": "ara2",
    "litio": "litio",
    "metotrexato": "metotrexato",
    "alopurinol": "alopurinol",
    "azatioprina": "azatioprina", "mercaptopurina": "azatioprina",
    "insulina": "insulina",
    "levotiroxina": "levotiroxina",
    "carbamazepina": "carbamazepina",
    "fenitoina": "fenitoina",
    "rifampicina": "rifampicina",
    "ciclosporina": "ciclosporina", "tacrolimus": "ciclosporina",
    "heparina": "heparina", "enoxaparina": "heparina",
    "vancomicina": "vancomicina",
    "gentamicina": "aminoglucosido", "amikacina": "aminoglucosido", "tobramicina": "aminoglucosido",
    "furosemida": "diuretico de asa",
    "prednisona": "corticoide", "dexametasona": "corticoide", "hidrocortisona": "corticoide",
    "diazepam": "benzodiacepina", "alprazolam": "benzodiacepina", "clonazepam": "benzodiacepina", "lorazepam": "benzodiacepina",
    "sucralfato": "sucralfato",
    "ketoconazol": "azol", "fluconazol": "azol", "itraconazol": "azol", "voriconazol": "azol",
    "metronidazol": "metronidazol",
    "teofilina": "teofilina",
    "verapamilo": "calcioantagonista no dihidropiridinico", "diltiazem": "calcioantagonista no dihidropiridinico",
}


def normalizar_nombre_farmaco(nombre: str) -> str:
    """Devuelve el nombre canónico (por clase, cuando aplica) usado como clave en BASE_INTERACCIONES."""
    clave = _normalizar(nombre)
    return ALIAS_FARMACOS.get(clave, clave)


def _par(a, b):
    return frozenset({a, b})


# Base curada: clave = frozenset de dos nombres canónicos.
BASE_INTERACCIONES = {
    _par("warfarina", "aspirina"): {
        "severidad": "Mayor", "mecanismo": "Efecto antiagregante + anticoagulante sumados",
        "efecto": "Riesgo aumentado de sangrado (GI y otros)",
        "recomendacion": "Evitar combinación salvo indicación específica; si se usa, vigilar INR y signos de sangrado.",
    },
    _par("warfarina", "ibuprofeno"): {
        "severidad": "Mayor", "mecanismo": "AINE desplaza warfarina de proteínas plasmáticas + daño de mucosa gástrica",
        "efecto": "Riesgo aumentado de sangrado GI",
        "recomendacion": "Evitar AINEs; considerar paracetamol para analgesia si es posible.",
    },
    _par("warfarina", "naproxeno"): {
        "severidad": "Mayor", "mecanismo": "Igual que otros AINEs: potenciación del efecto anticoagulante + riesgo GI",
        "efecto": "Riesgo aumentado de sangrado",
        "recomendacion": "Evitar combinación; considerar alternativa analgésica.",
    },
    _par("warfarina", "metronidazol"): {
        "severidad": "Mayor", "mecanismo": "Inhibición del metabolismo hepático (CYP2C9) de warfarina",
        "efecto": "Aumento del INR, riesgo de sangrado",
        "recomendacion": "Si es necesario usar juntos, monitorizar INR estrechamente y ajustar dosis.",
    },
    _par("warfarina", "macrolido"): {
        "severidad": "Moderada", "mecanismo": "Inhibición de CYP3A4 por macrólidos",
        "efecto": "Aumento del efecto anticoagulante",
        "recomendacion": "Monitorizar INR si se combinan; considerar azitromicina (menor interacción) sobre claritromicina.",
    },
    _par("clopidogrel", "omeprazol"): {
        "severidad": "Moderada", "mecanismo": "Omeprazol inhibe CYP2C19, reduciendo la activación de clopidogrel (profármaco)",
        "efecto": "Posible reducción del efecto antiagregante de clopidogrel",
        "recomendacion": "Preferir pantoprazol u otro IBP con menor interacción si se necesita protección gástrica.",
    },
    _par("estatina", "macrolido"): {
        "severidad": "Mayor", "mecanismo": "Inhibición de CYP3A4, aumenta niveles de estatina",
        "efecto": "Riesgo aumentado de miopatía/rabdomiólisis",
        "recomendacion": "Suspender temporalmente la estatina o usar una no metabolizada por CYP3A4 (ej. pravastatina).",
    },
    _par("sildenafilo", "nitratos"): {
        "severidad": "Mayor", "mecanismo": "Ambos aumentan GMPc, potenciando la vasodilatación",
        "efecto": "Hipotensión severa, potencialmente mortal",
        "recomendacion": "Contraindicado. No usar inhibidores de PDE5 con nitratos en ninguna ventana de tiempo cercana.",
    },
    _par("isrs", "imao"): {
        "severidad": "Mayor", "mecanismo": "Exceso de serotonina por doble mecanismo",
        "efecto": "Síndrome serotoninérgico (puede ser mortal)",
        "recomendacion": "Contraindicado combinar; respetar periodo de lavado (~2 semanas, 5 con fluoxetina) entre uno y otro.",
    },
    _par("isrs", "tramadol"): {
        "severidad": "Moderada", "mecanismo": "Tramadol tiene actividad serotoninérgica adicional",
        "efecto": "Riesgo aumentado de síndrome serotoninérgico",
        "recomendacion": "Usar con precaución; vigilar signos de síndrome serotoninérgico (agitación, hipertermia, clonus).",
    },
    _par("digoxina", "amiodarona"): {
        "severidad": "Mayor", "mecanismo": "Amiodarona reduce el aclaramiento renal y no renal de digoxina",
        "efecto": "Aumento de niveles de digoxina, riesgo de toxicidad",
        "recomendacion": "Reducir dosis de digoxina (~30-50%) al iniciar amiodarona; monitorizar niveles séricos.",
    },
    _par("digoxina", "diuretico de asa"): {
        "severidad": "Moderada", "mecanismo": "Hipopotasemia por diurético aumenta la sensibilidad miocárdica a digoxina",
        "efecto": "Riesgo aumentado de toxicidad digitálica (arritmias)",
        "recomendacion": "Monitorizar potasio sérico; suplementar si es necesario.",
    },
    _par("ieca", "ahorrador de potasio"): {
        "severidad": "Mayor", "mecanismo": "Ambos reducen la excreción de potasio por mecanismos distintos",
        "efecto": "Hiperpotasemia, riesgo de arritmias",
        "recomendacion": "Monitorizar potasio sérico y función renal si se combinan; usar con precaución.",
    },
    _par("ara2", "ahorrador de potasio"): {
        "severidad": "Mayor", "mecanismo": "Igual que IECA: reducción combinada de excreción de potasio",
        "efecto": "Hiperpotasemia",
        "recomendacion": "Monitorizar potasio sérico; evitar combinación en insuficiencia renal.",
    },
    _par("litio", "ieca"): {
        "severidad": "Moderada", "mecanismo": "IECA reduce el aclaramiento renal de litio",
        "efecto": "Aumento de niveles de litio, riesgo de toxicidad",
        "recomendacion": "Monitorizar niveles de litio al iniciar o ajustar el IECA.",
    },
    _par("litio", "diuretico de asa"): {
        "severidad": "Moderada", "mecanismo": "Depleción de sodio aumenta la reabsorción tubular de litio",
        "efecto": "Aumento de niveles de litio",
        "recomendacion": "Monitorizar niveles de litio y estado de hidratación.",
    },
    _par("metotrexato", "aspirina"): {
        "severidad": "Mayor", "mecanismo": "AINEs/salicilatos reducen el aclaramiento renal de metotrexato",
        "efecto": "Aumento de toxicidad de metotrexato (mielosupresión, mucositis)",
        "recomendacion": "Evitar en dosis altas de metotrexato (oncológicas); precaución incluso en dosis bajas (reumatológicas).",
    },
    _par("metotrexato", "ibuprofeno"): {
        "severidad": "Mayor", "mecanismo": "Igual mecanismo que con aspirina: reducción del aclaramiento renal",
        "efecto": "Aumento de toxicidad de metotrexato",
        "recomendacion": "Evitar combinación, especialmente con metotrexato en dosis altas.",
    },
    _par("azatioprina", "alopurinol"): {
        "severidad": "Mayor", "mecanismo": "Alopurinol inhibe la xantina oxidasa, que metaboliza azatioprina",
        "efecto": "Aumento marcado de niveles de azatioprina, riesgo de mielosupresión grave",
        "recomendacion": "Si es necesario combinar, reducir la dosis de azatioprina a ~25-33% de la habitual.",
    },
    _par("carbamazepina", "isrs"): {
        "severidad": "Moderada", "mecanismo": "Interacción variable según el ISRS (inhibición/inducción de CYP)",
        "efecto": "Niveles de carbamazepina alterados; riesgo de toxicidad o pérdida de eficacia",
        "recomendacion": "Monitorizar niveles de carbamazepina y respuesta clínica al iniciar o suspender el ISRS.",
    },
    _par("rifampicina", "warfarina"): {
        "severidad": "Mayor", "mecanismo": "Rifampicina es un potente inductor de CYP450, acelera el metabolismo de warfarina",
        "efecto": "Reducción marcada del efecto anticoagulante",
        "recomendacion": "Puede requerir aumentos importantes de dosis de warfarina; monitorizar INR de cerca.",
    },
    _par("ciclosporina", "azol"): {
        "severidad": "Mayor", "mecanismo": "Inhibición de CYP3A4 por antifúngicos azólicos",
        "efecto": "Aumento de niveles de ciclosporina/tacrolimus, riesgo de nefrotoxicidad",
        "recomendacion": "Ajustar dosis del inmunosupresor y monitorizar niveles séricos.",
    },
    _par("teofilina", "macrolido"): {
        "severidad": "Moderada", "mecanismo": "Inhibición de CYP1A2/3A4 por macrólidos",
        "efecto": "Aumento de niveles de teofilina, riesgo de toxicidad (náusea, arritmias, convulsiones)",
        "recomendacion": "Monitorizar niveles de teofilina; considerar azitromicina como alternativa.",
    },
    _par("calcioantagonista no dihidropiridinico", "digoxina"): {
        "severidad": "Moderada", "mecanismo": "Verapamilo/diltiazem reducen el aclaramiento de digoxina y suman efecto cronotrópico negativo",
        "efecto": "Aumento de niveles de digoxina + bradicardia excesiva",
        "recomendacion": "Monitorizar niveles de digoxina y frecuencia cardiaca.",
    },
    _par("insulina", "ieca"): {
        "severidad": "Menor", "mecanismo": "IECA puede aumentar levemente la sensibilidad a la insulina",
        "efecto": "Riesgo ligeramente aumentado de hipoglucemia",
        "recomendacion": "Vigilar glucemia al iniciar IECA en pacientes con insulina, especialmente en insuficiencia renal.",
    },
    _par("levotiroxina", "sucralfato"): {
        "severidad": "Moderada", "mecanismo": "Sucralfato reduce la absorción de levotiroxina",
        "efecto": "Reducción del efecto de levotiroxina",
        "recomendacion": "Separar la administración por al menos 4 horas.",
    },
    _par("heparina", "aspirina"): {
        "severidad": "Moderada", "mecanismo": "Efecto anticoagulante + antiagregante sumados",
        "efecto": "Riesgo aumentado de sangrado",
        "recomendacion": "Uso combinado frecuente en cardiología (ej. SICA) pero requiere vigilancia estrecha de sangrado.",
    },
    _par("vancomicina", "aminoglucosido"): {
        "severidad": "Mayor", "mecanismo": "Nefrotoxicidad y ototoxicidad aditivas",
        "efecto": "Riesgo aumentado de daño renal y auditivo",
        "recomendacion": "Monitorizar función renal y niveles séricos de ambos fármacos si se combinan.",
    },
    _par("metformina", "diuretico de asa"): {
        "severidad": "Menor", "mecanismo": "Interacción farmacocinética menor",
        "efecto": "Relevancia clínica limitada en la mayoría de los pacientes",
        "recomendacion": "No suele requerir ajuste; vigilar función renal como con cualquier paciente con metformina.",
    },
}


def verificar_interacciones(lista_farmacos: list) -> dict:
    """
    Recibe una lista de nombres de fármacos (texto libre, tal como los
    escribe el estudiante) y revisa TODOS los pares posibles contra
    BASE_INTERACCIONES.

    Devuelve {"encontradas": [...], "pares_sin_datos": [(a, b), ...],
    "farmacos_normalizados": {nombre_original: nombre_canonico}}.
    Nunca lanza excepción: nombres vacíos o duplicados se ignoran o
    deduplican en silencio.
    """
    nombres_limpios = [f.strip() for f in (lista_farmacos or []) if f and f.strip()]
    vistos = set()
    nombres_unicos = []
    for n in nombres_limpios:
        # Deduplicar por nombre CANÓNICO (post-alias), no por texto crudo:
        # "ASA" y "Aspirina" son el mismo fármaco y no deben generar un
        # par consigo mismo ni duplicar las interacciones encontradas.
        clave = normalizar_nombre_farmaco(n)
        if clave and clave not in vistos:
            vistos.add(clave)
            nombres_unicos.append(n)

    if len(nombres_unicos) < 2:
        return {
            "encontradas": [], "pares_sin_datos": [], "farmacos_normalizados": {},
            "error": "Escribe al menos dos fármacos (uno por línea).",
        }

    canonicos = {n: normalizar_nombre_farmaco(n) for n in nombres_unicos}

    encontradas = []
    pares_sin_datos = []
    for i in range(len(nombres_unicos)):
        for j in range(i + 1, len(nombres_unicos)):
            a, b = nombres_unicos[i], nombres_unicos[j]
            clave = _par(canonicos[a], canonicos[b])
            info = BASE_INTERACCIONES.get(clave)
            if info:
                encontradas.append({"farmaco_a": a, "farmaco_b": b, **info})
            else:
                pares_sin_datos.append((a, b))

    orden_severidad = {"Mayor": 0, "Moderada": 1, "Menor": 2}
    encontradas.sort(key=lambda x: orden_severidad.get(x["severidad"], 3))

    return {
        "encontradas": encontradas,
        "pares_sin_datos": pares_sin_datos,
        "farmacos_normalizados": canonicos,
    }


_INSTRUCCION_ANALISIS_IA_POR_IDIOMA = {
    "es": (
        "Eres un asistente educativo de farmacología. Te dan dos nombres de fármacos. "
        "Responde en ESPAÑOL, MUY brevemente (máximo 4-5 líneas), si existe una interacción "
        "clínicamente relevante conocida entre ellos: mecanismo, efecto esperado, y qué tan "
        "grave es (Mayor/Moderada/Menor/Ninguna conocida). Si no conoces una interacción "
        "relevante entre ellos, dilo explícitamente en vez de inventar una. No agregues "
        "advertencias genéricas largas, solo la información específica."
    ),
    "en": (
        "You are an educational pharmacology assistant. You are given two drug names. "
        "Answer in ENGLISH, VERY briefly (4-5 lines max), whether a clinically relevant known "
        "interaction exists between them: mechanism, expected effect, and how severe it is "
        "(Major/Moderate/Minor/None known). If you don't know of a relevant interaction between "
        "them, say so explicitly instead of inventing one. Don't add long generic warnings, just "
        "the specific information."
    ),
    "fr": (
        "Tu es un assistant éducatif en pharmacologie. On te donne deux noms de médicaments. "
        "Réponds en FRANÇAIS, TRÈS brièvement (4-5 lignes max), s'il existe une interaction "
        "cliniquement pertinente connue entre eux : mécanisme, effet attendu, et sa gravité "
        "(Majeure/Modérée/Mineure/Aucune connue). Si tu ne connais pas d'interaction pertinente "
        "entre eux, dis-le explicitement plutôt que d'en inventer une. N'ajoute pas de longs "
        "avertissements génériques, seulement l'information spécifique."
    ),
    "de": (
        "Du bist ein pädagogischer Pharmakologie-Assistent. Du bekommst zwei Medikamentennamen. "
        "Antworte AUF DEUTSCH, SEHR kurz (maximal 4-5 Zeilen), ob eine klinisch relevante bekannte "
        "Wechselwirkung zwischen ihnen besteht: Mechanismus, erwartete Wirkung, und wie schwerwiegend "
        "sie ist (Schwerwiegend/Mäßig/Gering/Keine bekannt). Wenn du keine relevante Wechselwirkung "
        "zwischen ihnen kennst, sag das ausdrücklich, statt eine zu erfinden. Füge keine langen "
        "allgemeinen Warnungen hinzu, nur die spezifische Information."
    ),
    "zh": (
        "你是一个药理学教育助手。你会收到两个药物名称。请用中文非常简短地回答（最多4-5行），"
        "说明它们之间是否存在已知的、具有临床意义的相互作用：机制、预期效果，以及严重程度"
        "（严重/中度/轻微/未知有相互作用）。如果你不知道它们之间有相关的相互作用，请明确说明，"
        "而不要编造一个。不要添加冗长的通用警告，只提供具体信息。"
    ),
}


def analizar_interaccion_con_ia(farmaco_a: str, farmaco_b: str, idioma: str = "es") -> dict:
    """
    Respaldo por IA SOLO para el par que no está en BASE_INTERACCIONES,
    y solo cuando la UI lo pide explícitamente. Devuelve
    {"disponible": bool, "texto": str, "diagnostico": str|None}.

    idioma: "es" (default), "en" o "fr" — controla tanto el idioma en el
    que el modelo redacta su análisis como los mensajes de diagnóstico
    de error. Un código no reconocido cae a español.

    El texto se etiqueta siempre como conocimiento general no verificado
    — nunca se presenta como si viniera de la base curada — siguiendo el
    mismo principio anti-alucinación que el resto de la app aplica a las
    respuestas sin evidencia citable.
    """
    if not client:
        return {"disponible": False, "texto": "", "diagnostico": t("groq_no_configurado", idioma)}
    instruccion = _INSTRUCCION_ANALISIS_IA_POR_IDIOMA.get(idioma, _INSTRUCCION_ANALISIS_IA_POR_IDIOMA["es"])
    try:
        respuesta = client.chat.completions.create(
            model=MODELO_AUXILIAR,
            messages=[
                {"role": "system", "content": instruccion},
                {"role": "user", "content": f"{farmaco_a} + {farmaco_b}"},
            ],
            max_tokens=220,
            temperature=0.2,
        )
        texto = (respuesta.choices[0].message.content or "").strip()
        if not texto:
            return {"disponible": False, "texto": "", "diagnostico": t("modelo_sin_texto", idioma)}
        return {"disponible": True, "texto": texto, "diagnostico": None}
    except Exception as ex:
        return {"disponible": False, "texto": "", "diagnostico": t("error_llamando_groq", idioma, error=ex)}
