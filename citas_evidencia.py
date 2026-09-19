"""
Formateadores de citas (Vancouver/APA), sistema de trazabilidad de
fuentes, chequeos determinísticos anti-alucinación (citas fuera de
rango, negación contradictoria) y el verificador de consistencia
fisiológica. También el juez de factualidad (LLM-as-judge) vía Groq.
"""
import re
import json

from config import client, MODELO_JUEZ, MAX_TOKENS_JUEZ, MAX_CHARS_EVAL_CONTEXTO, MAX_CHARS_ABSTRACT_CONTEXTO
from pubmed_search import clasificar_evidencia, _ORDEN_JERARQUIA_EVIDENCIA
from traducciones import t, t_categoria


def _autores_cita(autores, limite=6):
    """
    Convierte la lista de autores (JSON en la BD) a la forma corta de cita:
    'Apellido II, Apellido II' y agrega 'et al.' si hay más de `limite`.
    """
    if not autores:
        return ""
    nombres = []
    for a in autores[:limite]:
        apellido = a.get("apellido", "").strip()
        iniciales = a.get("iniciales", "").strip()
        nombre = f"{apellido} {iniciales}".strip() if iniciales else apellido
        if nombre:
            nombres.append(nombre)
    if len(autores) > limite:
        nombres.append("et al.")
    return ", ".join(nombres)

def formatear_cita_vancouver(p):
    """
    Cita en formato Vancouver (estándar biomédico, el mismo que usa
    PubMed). Ej.: 'Kahn SE, Cooper ME, Del Prato S. Pathophysiology and
    treatment of type 2 diabetes. Lancet. 2014;383(9922):1068-83.'
    Las piezas opcionales (revista/año/volumen/páginas/doi) se omiten si
    faltan, para que la cita quede siempre legible.
    """
    piezas = []
    autores = _autores_cita(p.get("autores", []))
    if autores:
        piezas.append(autores)
    if p.get("titulo"):
        piezas.append(p["titulo"])
    if p.get("revista"):
        piezas.append(p["revista"])
    detalle = ""
    if p.get("anio"):
        detalle = str(p["anio"])
    if p.get("volumen"):
        if detalle:
            detalle += ";"
        detalle += str(p["volumen"])
        if p.get("numero"):
            detalle += f"({p['numero']})"
    if p.get("paginas"):
        detalle += f":{p['paginas']}"
    if detalle:
        piezas.append(detalle + ".")
    if p.get("doi"):
        piezas.append(f"doi: {p['doi']}")
    return " ".join(piezas).strip()

def formatear_cita_apa(p):
    """
    Cita en formato APA 7. Ej.: 'Kahn, S. E., Cooper, M. E., & Del Prato,
    S. (2014). Pathophysiology and treatment of type 2 diabetes. The
    Lancet, 383(9922), 1068-1083. https://doi.org/10.1016/...'
    """
    autores = p.get("autores", [])
    piezas = []
    if autores:
        nombres_apa = []
        for a in autores[:6]:
            apellido = a.get("apellido", "")
            iniciales = a.get("iniciales", "")
            if iniciales:
                iniciales_punt = ". ".join(list(iniciales)) + "."
                nombres_apa.append(f"{apellido}, {iniciales_punt}")
            else:
                nombres_apa.append(apellido)
        if len(autores) > 6:
            nombres_apa.append("et al.")
        elif len(autores) > 1:
            nombres_apa[-1] = f"& {nombres_apa[-1]}"
        piezas.append(", ".join(nombres_apa))

    if p.get("anio"):
        piezas.append(f"({p['anio']}).")
    if p.get("titulo"):
        piezas.append(p["titulo"])
    if p.get("revista"):
        revista = p["revista"]
        if p.get("volumen"):
            revista += f", {p['volumen']}"
            if p.get("numero"):
                revista += f"({p['numero']})"
        if p.get("paginas"):
            revista += f", {p['paginas']}"
        piezas.append(revista + ".")
    if p.get("doi"):
        piezas.append(f"https://doi.org/{p['doi']}")
    return " ".join(piezas).strip()

def formatear_contexto_papers(papers, idioma="es"):
    """
    Convierte los papers rankeados en el bloque de texto numerado que se
    inyecta al modelo: [1], [2], ... con su cita Vancouver y su resumen.
    Es lo único del panel de PubMed que se persiste en el historial.
    """
    if not papers:
        return ""
    texto = (
        "📚 LITERATURA CIENTÍFICA MULTIFUENTE (ordenada por relevancia semántica):\n\n"
        "Criterio de agrupación: se seleccionaron por relevancia, recencia y disponibilidad "
        "en las fuentes consultadas, no por coherencia temática.\n\n"
    )
    for i, p in enumerate(papers, start=1):
        score = p.get("score")
        relevancia = f" (relevancia {score * 100:.0f}%)" if score is not None else ""
        texto += (
            f"[{i}]{relevancia}\n"
            f"ID DE REFERENCIA INMUTABLE: [{i}] — usa exactamente este número; "
            "no renumeres ni reordenes las referencias. Solo inclúyela en la lista final "
            "si la citas explícitamente en el cuerpo.\n"
        )
        texto += formatear_cita_vancouver(p) + "\n"
        texto += f"Revista (metadatos): {p.get('revista') or '[nombre no disponible en los metadatos]'}\n"
        texto += f"Fuente de recuperación: {p.get('fuente_bd') or 'PubMed'}\n"
        if "desolation" in (p.get("titulo") or "").lower():
            texto += (
                "Nota del título: [posible artefacto de traducción en el título; "
                "verificar contra el artículo original]\n"
            )
        categoria = clasificar_evidencia(p.get("tipos_publicacion", []))
        texto += f"{t('nivel_evidencia', idioma)}: {t_categoria(categoria, idioma)}\n"
        identificadores = []
        if p.get("pmid"):
            identificadores.append(f"PMID: {p['pmid']}")
        if p.get("doi"):
            identificadores.append(f"DOI: {p['doi']}")
        if identificadores:
            texto += " | ".join(identificadores) + "\n"
        if p.get("resumen"):
            texto += f"Resumen: {p['resumen'][:MAX_CHARS_ABSTRACT_CONTEXTO]}\n"
        texto += "\n"
    return texto


def detectar_citas_en_respuesta(respuesta: str, n_papers: int, n_fragmentos: int) -> set:
    """
    Escanea el texto de la respuesta buscando [1], [2]... (papers) y
    [F1], [F2]... (fragmentos de PDF). Devuelve un set de tuplas
    ("paper", n) / ("fragmento", n) con lo que el modelo citó realmente,
    para poder marcar en el panel de fuentes qué se usó de verdad y qué
    solo estaba disponible como contexto.
    """
    citas = set()
    for num in range(1, n_papers + 1):
        if re.search(rf"\[\s*{num}\s*\]", respuesta):
            citas.add(("paper", num))
    for num in range(1, n_fragmentos + 1):
        if re.search(rf"\[\s*F{num}\s*\]", respuesta, re.IGNORECASE):
            citas.add(("fragmento", num))
    return citas

def detectar_citas_alucinadas(respuesta: str, n_papers: int, n_fragmentos: int) -> bool:
    """
    Chequeo determinístico (no depende de que el modelo obedezca el
    prompt ni de que el juez LLM esté disponible): si la respuesta trae
    patrones de cita [1], [2], [F1]... pero no había NINGÚN paper ni
    fragmento real en el contexto de este turno, esas citas son
    inventadas por definición.
    """
    if n_papers > 0 or n_fragmentos > 0:
        return False
    return bool(re.search(r"\[\s*F?\d+\s*\]", respuesta))

def detectar_citas_fuera_de_rango(respuesta: str, n_papers: int, n_fragmentos: int) -> dict:
    """
    Validación por regex, determinística: extrae TODOS los números que el
    modelo puso entre [n] (papers) y [Fn] (fragmentos) en su respuesta y
    verifica que cada número exista de verdad dentro del rango de fuentes
    que se le entregaron ese turno (1..n_papers / 1..n_fragmentos).

    Esto atrapa un caso más sutil que detectar_citas_alucinadas: aquí SÍ
    había contexto real (por eso ese chequeo no dispara), pero el modelo
    citó un número que no corresponde a ninguna fuente entregada — por
    ejemplo [5] cuando solo se le dieron 3 papers.

    Devuelve {"papers_invalidos": [...], "fragmentos_invalidos": [...]}
    (listas vacías si todas las citas son válidas).
    """
    papers_citados = {int(n) for n in re.findall(r"\[\s*(\d+)\s*\]", respuesta)}
    fragmentos_citados = {int(n) for n in re.findall(r"\[\s*F(\d+)\s*\]", respuesta, re.IGNORECASE)}
    return {
        "papers_invalidos": sorted(n for n in papers_citados if n < 1 or n > n_papers),
        "fragmentos_invalidos": sorted(n for n in fragmentos_citados if n < 1 or n > n_fragmentos),
    }


def eliminar_referencias_no_citadas(respuesta: str) -> str:
    """
    Elimina de la sección final de referencias las entradas que no aparecen
    citadas en el cuerpo. Conserva los IDs originales para no desalinear
    las citas válidas.
    """
    encabezado = re.search(
        r"(?im)^(?:#{0,6}\s*)?(?:\*\*)?\s*(?:referencias|references|références|referenzen|参考文献)\s*:?\s*(?:\*\*)?\s*$",
        respuesta,
    )
    if not encabezado:
        return respuesta

    cuerpo = respuesta[:encabezado.start()]
    citadas = {
        int(n)
        for n in re.findall(r"\[\s*(\d+)\s*\]", cuerpo)
    }
    cola = respuesta[encabezado.end():]
    patron_entrada = re.compile(
        r"(?m)^\s*(?:\*\*)?(?:\[(\d+)\]|(\d+)[.)])(?:\*\*)?\s*"
    )
    entradas = list(patron_entrada.finditer(cola))
    if not entradas:
        return respuesta

    partes = []
    inicio = 0
    for indice, entrada in enumerate(entradas):
        if entrada.start() > inicio:
            partes.append(cola[inicio:entrada.start()])
        siguiente = (
            entradas[indice + 1].start()
            if indice + 1 < len(entradas)
            else len(cola)
        )
        numero = int(entrada.group(1) or entrada.group(2))
        if numero in citadas:
            partes.append(cola[entrada.start():siguiente])
        inicio = siguiente
    return cuerpo + respuesta[encabezado.start():encabezado.end()] + "".join(partes)

_PATRONES_NEGACION_EVIDENCIA = [
    r"no encontr[ée] papers",
    r"no encontr[ée] evidencia",
    r"no tengo papers verificados",
    r"no tengo evidencia",
    r"sin (acceso a |ning[uú]n )?papers?",
    r"did\s*n['’]?t find (any )?(PubMed )?papers",
    r"did not find (any )?(PubMed )?papers",
    r"could\s*n['’]?t find (any )?evidence",
    r"no verified papers",
    r"without (access to )?(any )?papers?",
    r"no papers (were )?found",
    r"n['’]ai (pas )?trouv[ée] .{0,15}articles?",
    r"aucun article .{0,10}trouv[ée]",
    r"pas de preuves? v[ée]rifi[ée]es?",
    r"sans (acc[èe]s [àa] )?(aucun )?articles?",
    r"keine (PubMed[- ])?(studien|artikel|papers?).{0,30}gefunden",
    r"keine (verifizierte[n]? )?evidenz",
    r"ohne (zugriff auf )?(irgendwelche )?(studien|artikel|papers?)",
    r"konnte keine (evidenz|studien|artikel) finden",
    r"没有找到.{0,25}(文献|论文|证据)",
    r"没有.{0,5}证据",
    r"未找到.{0,10}(文献|论文)",
    r"无法找到.{0,10}(文献|证据)",
]

def detectar_negacion_contradictoria(respuesta: str, n_papers: int, n_fragmentos: int) -> bool:
    """
    Chequeo determinístico: si SÍ había papers o fragmentos reales en el
    contexto de este turno, pero la respuesta igual abre diciendo que no
    encontró evidencia, es una contradicción del modelo consigo mismo —
    repitió la frase de apertura de memoria sin fijarse en que esta vez SÍ
    había contexto (a veces incluso cita ese contexto correctamente más
    abajo en la misma respuesta, como pasó en pruebas reales).
    """
    if n_papers == 0 and n_fragmentos == 0:
        return False
    return any(re.search(patron, respuesta, re.IGNORECASE) for patron in _PATRONES_NEGACION_EVIDENCIA)


_PATRONES_FRASE_NEGACION_COMPLETA = [
    re.compile(r"No encontr[ée] papers de PubMed para citar en esta consulta[^.]*\.\s*", re.IGNORECASE),
    re.compile(r"I did\s*n['’]?t find (any )?PubMed papers to cite for this (query|question)[^.]*\.\s*", re.IGNORECASE),
    re.compile(r"Je n['’]?ai trouv[ée] aucun article PubMed [^.]*\.\s*", re.IGNORECASE),
    re.compile(r"Ich habe für diese Anfrage keine PubMed-Studien zum Zitieren gefunden[^.]*\.\s*", re.IGNORECASE),
    re.compile(r"我没有找到可以为此次咨询引用的\s*PubMed\s*文献[^。]*。\s*"),
]

def limpiar_negacion_contradictoria(respuesta: str, n_papers: int, n_fragmentos: int) -> str:
    """
    Si detectar_negacion_contradictoria() da True, quita del texto la
    frase de apertura falsa ("No encontré papers.../I didn't find.../Je
    n'ai trouvé...") en vez de dejarla ahí sabiendo que es incorrecta —
    no tiene caso mostrarle al estudiante una negación falsa cuando el
    panel de Fuentes de abajo va a mostrar los papers reales de todos
    modos. Prueba los 3 patrones exactos (uno por idioma soportado); si
    el modelo parafraseó la frase de forma distinta a los tres, se
    devuelve el texto sin tocar (la alerta de contradicción sigue
    funcionando igual, solo no se logra limpiar automáticamente).
    """
    if n_papers == 0 and n_fragmentos == 0:
        return respuesta
    for patron in _PATRONES_FRASE_NEGACION_COMPLETA:
        limpio = patron.sub("", respuesta, count=1)
        if limpio != respuesta:
            return limpio.lstrip()
    return respuesta


REGLAS_FISIOLOGICAS = {
    "conn": {
        "nombre_mostrar": "Síndrome de Conn / Hiperaldosteronismo primario",
        "alias": [r"s[ií]ndrome\s+de\s+conn", r"hiperaldosteronismo\s+primario"],
        "incompatible_con": {
            "hiperpotasemia": "El hiperaldosteronismo primario causa PÉRDIDA renal de potasio (hipopotasemia), no retención.",
            "hipotension": "El exceso de aldosterona retiene sodio y agua, lo que causa HIPERtensión, no hipotensión.",
        },
    },
    "addison": {
        "nombre_mostrar": "Insuficiencia suprarrenal (Addison)",
        "alias": [r"enfermedad\s+de\s+addison", r"insuficiencia\s+suprarrenal(\s+primaria)?"],
        "incompatible_con": {
            "hipertension": "La deficiencia de aldosterona en Addison causa pérdida de sodio e HIPOtensión, no hipertensión.",
            "hipopotasemia": "Addison típicamente causa hiperpotasemia (falta de aldosterona), no hipopotasemia.",
        },
    },
    "cushing": {
        "nombre_mostrar": "Síndrome de Cushing",
        "alias": [r"s[ií]ndrome\s+de\s+cushing"],
        "incompatible_con": {
            "hipotension": "El exceso de cortisol (con su efecto mineralocorticoide) causa HIPERtensión en Cushing, no hipotensión.",
        },
    },
    "hipertiroidismo": {
        "nombre_mostrar": "Hipertiroidismo",
        "alias": [r"hipertiroidismo", r"tirotoxicosis"],
        "incompatible_con": {
            "bradicardia": "El exceso de hormona tiroidea acelera el metabolismo y causa taquicardia, no bradicardia.",
        },
    },
    "hipotiroidismo": {
        "nombre_mostrar": "Hipotiroidismo",
        "alias": [r"hipotiroidismo"],
        "incompatible_con": {
            "taquicardia": "El hipotiroidismo típicamente causa bradicardia, no taquicardia.",
        },
    },
}

_PATRONES_HALLAZGOS = {
    "hiperpotasemia": r"potasio\s+(alto|elevado)|hiperpotasemia|hiperkalemia|hiperkaliemia",
    "hipopotasemia": r"potasio\s+(bajo|disminuido)|hipopotasemia|hipokalemia|hipokaliemia",
    "hipertension": r"hipertensi[oó]n(?!\s+ortost)|presi[oó]n\s+arterial\s+alta",
    "hipotension": r"hipotensi[oó]n|presi[oó]n\s+arterial\s+baja",
    "bradicardia": r"bradicardia|frecuencia\s+cardiaca\s+baja",
    "taquicardia": r"taquicardia|frecuencia\s+cardiaca\s+alta",
}

def verificar_consistencia_fisiologica(pregunta: str, respuesta: str) -> list:
    """
    Cruza los hallazgos clínicos mencionados en la PREGUNTA del usuario
    contra los diagnósticos que la RESPUESTA del modelo propone, usando
    REGLAS_FISIOLOGICAS. Devuelve una lista de contradicciones detectadas
    (vacía si no hay ninguna o si no aplica ningún diagnóstico del
    catálogo). No es una verificación clínica completa — solo atrapa las
    incompatibilidades de manual más clásicas.
    """
    hallazgos = {
        nombre for nombre, patron in _PATRONES_HALLAZGOS.items()
        if re.search(patron, pregunta, re.IGNORECASE)
    }
    if not hallazgos:
        return []

    contradicciones = []
    for regla in REGLAS_FISIOLOGICAS.values():
        if not any(re.search(alias, respuesta, re.IGNORECASE) for alias in regla["alias"]):
            continue
        for hallazgo in hallazgos:
            if hallazgo in regla["incompatible_con"]:
                contradicciones.append({
                    "diagnostico": regla["nombre_mostrar"],
                    "hallazgo": hallazgo,
                    "explicacion": regla["incompatible_con"][hallazgo],
                })
    return contradicciones

def construir_lista_fuentes(papers, fragmentos, respuesta: str) -> list:
    """
    Arma la lista de fuentes (papers + fragmentos de PDF) que se usaron
    para responder, marcando cuáles fueron citadas explícitamente con
    [n]/[Fn] y cuáles solo estaban disponibles como contexto. Esto es lo
    que se persiste junto al mensaje del asistente y se muestra en el
    panel "Fuentes de esta respuesta".
    """
    citadas = detectar_citas_en_respuesta(respuesta, len(papers), len(fragmentos))
    fuentes = []
    for i, p in enumerate(papers, start=1):
        fuentes.append({
            "tipo": "paper",
            "indice": i,
            "pmid": p.get("pmid"),
            "doi": p.get("doi"),
            "fuente_bd": p.get("fuente_bd"),
            "titulo": p.get("titulo", ""),
            "nivel_evidencia": clasificar_evidencia(p.get("tipos_publicacion", [])),
            "citado": ("paper", i) in citadas,
        })
    for j, (similitud, fuente, texto_frag, tipo_texto) in enumerate(fragmentos, start=1):
        fuentes.append({
            "tipo": "fragmento_pdf",
            "indice": j,
            "fuente": fuente,
            "similitud": similitud,
            "via_ocr": tipo_texto == "ocr",
            "snippet": (texto_frag or "")[:150],
            "citado": ("fragmento", j) in citadas,
        })
    return fuentes


def resumen_evidencia_citada(fuentes: list) -> dict:
    """
    Recomendación externa (prioridad 2): "ya tienes el metadata de
    PubMed (tipo de estudio), etiquetar la respuesta con RCT/Meta-
    análisis/Caso es un parseo de 1 campo" — exacto, cada fuente en
    'fuentes' ya trae 'nivel_evidencia' y 'citado' desde
    construir_lista_fuentes(); esta función solo agrega el nivel MÁS
    FUERTE entre los papers que el modelo citó de verdad (no todos los
    que se recuperaron, solo los citados con [n]) para mostrar un
    badge de un vistazo al final de la respuesta.

    Devuelve:
      {"disponible": False} si no hay ningún paper citado (ej. la
      respuesta se basó solo en conocimiento general o en fragmentos
      de PDF del estudiante).
      {"disponible": True, "nivel_mas_fuerte": str, "n_papers_citados": int,
       "niveles_presentes": [str, ...]} si sí hay.

    "niveles_presentes" viene ordenado de más a menos fuerte (mismo
    orden que _ORDEN_JERARQUIA_EVIDENCIA), sin duplicados.
    """
    papers_citados = [f for f in fuentes if f.get("tipo") == "paper" and f.get("citado")]
    if not papers_citados:
        return {"disponible": False}

    def _posicion_jerarquia(nivel):
        try:
            return _ORDEN_JERARQUIA_EVIDENCIA.index(nivel)
        except ValueError:
            return len(_ORDEN_JERARQUIA_EVIDENCIA)

    niveles_unicos = []
    vistos = set()
    for f in sorted(papers_citados, key=lambda f: _posicion_jerarquia(f["nivel_evidencia"])):
        nivel = f["nivel_evidencia"]
        if nivel not in vistos:
            vistos.add(nivel)
            niveles_unicos.append(nivel)

    return {
        "disponible": True,
        "nivel_mas_fuerte": niveles_unicos[0],
        "n_papers_citados": len(papers_citados),
        "niveles_presentes": niveles_unicos,
    }

def construir_contexto_para_juez_desde_fuentes_crudas(papers, fragmentos) -> str:
    """
    Reconstruye el bloque de fuentes desde los papers/fragmentos crudos,
    con su propio recorte de 1200 caracteres por resumen — MÁS GRANDE
    que los 600 caracteres (MAX_CHARS_ABSTRACT_CONTEXTO) que de verdad
    recibió el generador en formatear_contexto_papers().

    Feedback externo (John6666, foro de Hugging Face, prioridad 2): esta
    era la función que se usaba antes para armar el contexto del juez de
    factualidad, y responde a una pregunta distinta de "¿la respuesta
    fue fiel a lo que el generador realmente vio?" — responde más bien
    "¿la respuesta es compatible con toda la evidencia que la app pudo
    reunir en algún punto de la búsqueda?" (evaluación de corrección más
    amplia, no de fidelidad). Además, al truncar el string ya unido a
    MAX_CHARS_EVAL_CONTEXTO de un tirón, los fragmentos de PDF (que se
    agregan después de los papers) podían desaparecer del todo si los
    abstracts de los papers ya llenaban el cupo.

    Se conserva por si en el futuro se quiere ese chequeo más amplio
    como métrica separada, pero el juez de factualidad por default usa
    construir_contexto_para_juez() de abajo, que reutiliza el contexto
    exacto que ya vio el generador (fidelidad/faithfulness).
    """
    partes = []
    for i, p in enumerate(papers, start=1):
        resumen = (p.get("resumen") or "")[:1200]
        partes.append(
            f"[{i}] {p.get('titulo', '')} ({p.get('revista', '')} {p.get('anio', '')}). "
            f"Nivel de evidencia: {clasificar_evidencia(p.get('tipos_publicacion', []))}. "
            f"Resumen: {resumen}"
        )
    for j, (similitud, fuente, texto_frag, tipo_texto) in enumerate(fragmentos, start=1):
        partes.append(f"[F{j}] Fuente: {fuente}. Texto: {(texto_frag or '')[:1200]}")
    return "\n\n".join(partes)[:MAX_CHARS_EVAL_CONTEXTO]


def construir_contexto_para_juez(contexto_pubmed: str, bloque_pdf: str) -> str:
    """
    Arma el contexto que se le da al juez de factualidad reutilizando el
    MISMO texto — mismos recortes de abstract, mismos fragmentos [Fn] —
    que ya se le mandó al generador (contexto_pubmed de
    formatear_contexto_papers() y bloque_pdf armado en app_ui.py), en
    vez de reconstruirlo desde cero con otros límites de caracteres.

    Esto responde a "¿la respuesta fue fiel a la evidencia que el
    generador REALMENTE recibió?" (fidelidad), que es la pregunta que
    tiene sentido para un juez que corre inmediatamente después de esa
    generación. La pregunta más amplia — "¿es compatible con toda la
    evidencia que la app pudo reunir?" — es otra métrica, y quedaría
    para construir_contexto_para_juez_desde_fuentes_crudas() si algún
    día se quiere por separado.

    Si el total excede MAX_CHARS_EVAL_CONTEXTO, se recorta cada bloque
    (papers, PDF) en proporción a su tamaño en vez de cortar el string
    final ya unido de un tirón — así un bloque no desaparece solo por
    venir después en la concatenación.
    """
    bloques = [b for b in (contexto_pubmed or "", bloque_pdf or "") if b.strip()]
    if not bloques:
        return ""
    total_chars = sum(len(b) for b in bloques)
    if total_chars <= MAX_CHARS_EVAL_CONTEXTO:
        return "\n\n".join(bloques)
    partes = []
    for b in bloques:
        cupo = max(200, int(MAX_CHARS_EVAL_CONTEXTO * (len(b) / total_chars)))
        partes.append(b[:cupo])
    return "\n\n".join(partes)

def _parsear_json_juez(texto: str):
    """Extrae el primer bloque {...} del texto del juez y lo parsea como
    JSON. Nunca lanza excepción: devuelve None si algo no calza."""
    if not texto:
        return None
    try:
        inicio = texto.find("{")
        fin = texto.rfind("}") + 1
        if inicio == -1 or fin <= inicio:
            return None
        return json.loads(texto[inicio:fin])
    except Exception:
        return None

def evaluar_factualidad(respuesta: str, contexto_fuentes: str):
    """
    Evaluación automática de factualidad (LLM-as-judge): le pide a Groq
    que compare cada afirmación de la respuesta contra las fuentes
    numeradas y la clasifique como Soportada / No soportada / No
    verificable, con un score global 0-100.

    Devuelve un dict {"score", "afirmaciones", "resumen"} o None si el
    juez no está disponible o falla — nunca interrumpe el flujo del chat.
    """
    if not client or not contexto_fuentes.strip():
        return None
    prompt = (
        "Eres un juez médico riguroso. Compara CADA afirmación clínica de la "
        "respuesta del asistente contra las fuentes numeradas que se te dan.\n\n"
        "No uses conocimiento externo para validar una afirmación. Para cada afirmación cuantitativa "
        "o comparativa (ranking, porcentaje, conteo, fecha, 'más común', 'top' o 'principal'), "
        "verifica que la fuente respalde exactamente la misma población, geografía, periodo y medida. "
        "Si la fuente solo habla de Estados Unidos, no la aceptes como evidencia de países de altos "
        "ingresos o del mundo. Si el resumen no contiene el dato exacto, clasifícala como No verificable, "
        "aunque la afirmación parezca médicamente plausible. No corrijas la respuesta usando memoria: "
        "identifica la afirmación no respaldada y explica qué alcance falta.\n\n"
        "Clasifica cada afirmación como: Soportada | No soportada | No verificable.\n\n"
        "Devuelve EXCLUSIVAMENTE JSON con este formato exacto, sin texto extra:\n"
        '{"score": <0-100>, "afirmaciones": ['
        '{"afirmacion": "...", "estado": "Soportada", "fuente": "[1] o [F2] o null"}'
        '], "resumen": "..."}\n\n'
        "El score global debe penalizar afirmaciones 'No soportada' y 'No verificable'.\n\n"
        f"=== FUENTES ===\n{contexto_fuentes}\n\n"
        f"=== RESPUESTA DEL ASISTENTE ===\n{respuesta}"
    )
    try:
        respuesta_juez = client.chat.completions.create(
            model=MODELO_JUEZ,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=MAX_TOKENS_JUEZ,
        )
        return _parsear_json_juez(respuesta_juez.choices[0].message.content or "")
    except Exception:
        return None
