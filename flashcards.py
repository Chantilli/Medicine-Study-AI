"""
Flashcards y repetición espaciada (Fase 4).

Dos responsabilidades separadas en este módulo:

1. CRUD de flashcards — crearlas a mano, generarlas con IA a partir de un
   tema o texto (ej. un PDF ya indexado), listarlas, borrarlas.

2. Algoritmo SM-2 (SuperMemo 2) de repetición espaciada — el mismo
   algoritmo clásico que usan Anki y herramientas similares. Es
   puramente matemático/determinístico, no depende de ningún modelo de
   IA ni llamada de red, así que es instantáneo y no le pesa nada al
   servidor.

Cómo funciona SM-2 en resumen: cada vez que repasas una tarjeta, calificas
qué tan bien la recordaste (0 a 5). Si te fue bien (≥3), el intervalo
hasta el próximo repaso crece (1 día → 6 días → intervalo × facilidad...);
si te fue mal (<3), se reinicia a 1 día. La "facilidad" de cada tarjeta
se ajusta con cada repaso: tarjetas que te cuestan más se repiten más
seguido; las que dominas, más espaciadas.
"""
import json
import sqlite3
from datetime import date, timedelta

from database import DB_PATH
from config import client, MODELO_AUXILIAR


def crear_flashcard(usuario_id, pregunta: str, respuesta: str, tema: str = None, fuente: str = None) -> int:
    """Crea una flashcard nueva, lista para repasar desde hoy. Devuelve su id."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO flashcards (usuario_id, pregunta, respuesta, tema, fuente) VALUES (?, ?, ?, ?, ?)",
        (usuario_id, pregunta.strip(), respuesta.strip(), tema, fuente)
    )
    conn.commit()
    nuevo_id = cursor.lastrowid
    conn.close()
    return nuevo_id

def obtener_flashcards_pendientes(usuario_id, hasta_fecha: str = None) -> list:
    """
    Devuelve las flashcards cuya proxima_revision ya llegó (por defecto,
    hoy o antes — las atrasadas también cuentan, igual que en Anki).
    """
    hasta_fecha = hasta_fecha or date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM flashcards WHERE usuario_id = ? AND proxima_revision <= ? ORDER BY proxima_revision ASC",
        (usuario_id, hasta_fecha)
    )
    filas = [dict(f) for f in cursor.fetchall()]
    conn.close()
    return filas

def contar_flashcards_pendientes(usuario_id) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM flashcards WHERE usuario_id = ? AND proxima_revision <= ?",
        (usuario_id, date.today().isoformat())
    )
    total = cursor.fetchone()[0]
    conn.close()
    return total

def obtener_todas_las_flashcards(usuario_id) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM flashcards WHERE usuario_id = ? ORDER BY fecha_creacion DESC",
        (usuario_id,)
    )
    filas = [dict(f) for f in cursor.fetchall()]
    conn.close()
    return filas

def eliminar_flashcard(usuario_id, flashcard_id) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM flashcards WHERE id = ? AND usuario_id = ?", (flashcard_id, usuario_id))
    conn.commit()
    conn.close()


def _parsear_json_flashcards(texto: str):
    """Parseo tolerante del JSON que devuelve el modelo — nunca lanza excepción."""
    if not texto:
        return None
    try:
        inicio = texto.find("[")
        fin = texto.rfind("]") + 1
        if inicio == -1 or fin <= inicio:
            return None
        return json.loads(texto[inicio:fin])
    except Exception:
        return None

_INSTRUCCIONES_FLASHCARDS_POR_IDIOMA = {
    "es": (
        "Eres un asistente que genera material de estudio médico. A partir del texto que te den, genera "
        "EXACTAMENTE {n} flashcards (pregunta y respuesta), EN ESPAÑOL, que cubran los conceptos más "
        "importantes para memorizar — hechos concretos, mecanismos, valores, criterios diagnósticos, no "
        "preguntas triviales de sí/no. La pregunta debe poder responderse sin ver el texto original, y la "
        "respuesta debe ser corta y precisa (1-3 oraciones), no un párrafo largo.\n\n"
        "Devuelve EXCLUSIVAMENTE un array JSON con este formato exacto, sin texto antes ni después, sin "
        "markdown, sin explicar tu razonamiento:\n"
        '[{{"pregunta": "...", "respuesta": "..."}}, ...]'
    ),
    "en": (
        "You are an assistant that generates medical study material. From the text given to you, generate "
        "EXACTLY {n} flashcards (question and answer), IN ENGLISH, covering the most important concepts to "
        "memorize — concrete facts, mechanisms, values, diagnostic criteria, not trivial yes/no questions. "
        "The question must be answerable without seeing the original text, and the answer must be short and "
        "precise (1-3 sentences), not a long paragraph.\n\n"
        "Return ONLY a JSON array in this exact format, no text before or after, no markdown, no explaining "
        "your reasoning:\n"
        '[{{"pregunta": "...", "respuesta": "..."}}, ...]'
    ),
    "fr": (
        "Tu es un assistant qui génère du matériel d'étude médical. À partir du texte fourni, génère "
        "EXACTEMENT {n} flashcards (question et réponse), EN FRANÇAIS, couvrant les concepts les plus "
        "importants à mémoriser — faits concrets, mécanismes, valeurs, critères diagnostiques, pas de "
        "questions triviales oui/non. La question doit pouvoir être répondue sans voir le texte original, "
        "et la réponse doit être courte et précise (1-3 phrases), pas un long paragraphe.\n\n"
        "Retourne UNIQUEMENT un tableau JSON dans ce format exact, sans texte avant ni après, sans markdown, "
        "sans expliquer ton raisonnement :\n"
        '[{{"pregunta": "...", "respuesta": "..."}}, ...]'
    ),
    "de": (
        "Du bist ein Assistent, der medizinisches Lernmaterial erstellt. Erstelle aus dem gegebenen Text "
        "GENAU {n} Karteikarten (Frage und Antwort), AUF DEUTSCH, die die wichtigsten zu merkenden Konzepte "
        "abdecken — konkrete Fakten, Mechanismen, Werte, diagnostische Kriterien, keine trivialen "
        "Ja/Nein-Fragen. Die Frage muss beantwortbar sein, ohne den Originaltext zu sehen, und die Antwort "
        "muss kurz und präzise sein (1-3 Sätze), kein langer Absatz.\n\n"
        "Gib AUSSCHLIESSLICH ein JSON-Array in diesem exakten Format zurück, ohne Text davor oder danach, "
        "ohne Markdown, ohne deine Überlegungen zu erklären:\n"
        '[{{"pregunta": "...", "respuesta": "..."}}, ...]'
    ),
    "zh": (
        "你是一个生成医学学习资料的助手。请根据给定的文本，用中文生成正好 {n} 张记忆卡（问题和答案），"
        "涵盖最需要记忆的重要概念——具体事实、机制、数值、诊断标准，不要出琐碎的是/否问题。问题应该在不看"
        "原文的情况下也能回答，答案应该简短精确（1-3句话），不要写成长段落。\n\n"
        "只返回严格符合以下格式的 JSON 数组，前后不要有任何文字，不要用 markdown，不要解释你的推理过程：\n"
        '[{{"pregunta": "...", "respuesta": "..."}}, ...]'
    ),
}


def generar_flashcards_con_ia(usuario_id, texto_fuente: str, tema: str = None, fuente: str = None,
                                n: int = 5, idioma: str = "es"):
    """
    Le pide a Groq que genere N flashcards (pregunta/respuesta) a partir
    de un texto — puede ser un tema libre que el estudiante escribió, o
    contenido real de un PDF ya indexado (fragmentos recuperados). Cada
    flashcard se guarda de inmediato en la base de datos.

    idioma: "es" (default), "en" o "fr" — controla en qué idioma el
    modelo redacta pregunta/respuesta. Un código no reconocido cae a
    español, igual que construir_system_prompt() en config.py.

    Devuelve (lista_creadas, diagnostico). lista_creadas son dicts con su
    id (vacía si algo falló). diagnostico es None si todo salió bien, o
    un string explicando qué pasó (excepción real, o un preview de lo que
    contestó el modelo si no se pudo parsear como la lista de flashcards
    esperada) — nunca lanza excepción, pero tampoco falla en silencio.
    """
    if not client:
        return [], "El cliente de Groq no está configurado (falta GROQ_API_KEY)."
    if not texto_fuente or not texto_fuente.strip():
        return [], "No había texto fuente para generar flashcards."
    plantilla = _INSTRUCCIONES_FLASHCARDS_POR_IDIOMA.get(idioma, _INSTRUCCIONES_FLASHCARDS_POR_IDIOMA["es"])
    try:
        respuesta = client.chat.completions.create(
            model=MODELO_AUXILIAR,
            messages=[
                {"role": "system", "content": plantilla.format(n=n)},
                {"role": "user", "content": texto_fuente[:4000]},
            ],
            max_tokens=1200,
            temperature=0.3,
        )
        contenido = respuesta.choices[0].message.content or ""
        datos = _parsear_json_flashcards(contenido)
        if not isinstance(datos, list):
            preview = contenido[:300].replace("\n", " ")
            return [], f"El modelo no devolvió una lista JSON válida. Respuesta cruda: {preview!r}"
        creadas = []
        for item in datos:
            if not isinstance(item, dict):
                continue
            pregunta = (item.get("pregunta") or "").strip()
            respuesta_txt = (item.get("respuesta") or "").strip()
            if not pregunta or not respuesta_txt:
                continue
            nuevo_id = crear_flashcard(usuario_id, pregunta, respuesta_txt, tema=tema, fuente=fuente)
            creadas.append({"id": nuevo_id, "pregunta": pregunta, "respuesta": respuesta_txt})
        if not creadas:
            preview = contenido[:300].replace("\n", " ")
            return [], f"El modelo devolvió una lista pero ninguna tarjeta tenía pregunta y respuesta válidas. Respuesta cruda: {preview!r}"
        return creadas, None
    except Exception as ex:
        return [], f"Error llamando a Groq: {ex}"


def calcular_sm2(facilidad: float, intervalo: int, repeticiones: int, calidad: int):
    """
    Implementación estándar de SM-2. `calidad` va de 0 a 5:
      0-2 = no la recordaste (reinicia el ciclo)
      3-5 = sí la recordaste, con distinto grado de esfuerzo

    Devuelve (nueva_facilidad, nuevo_intervalo, nuevas_repeticiones).
    """
    calidad = max(0, min(5, calidad))

    if calidad < 3:
        
        nuevas_repeticiones = 0
        nuevo_intervalo = 1
    else:
        nuevas_repeticiones = repeticiones + 1
        if nuevas_repeticiones == 1:
            nuevo_intervalo = 1
        elif nuevas_repeticiones == 2:
            nuevo_intervalo = 6
        else:
            nuevo_intervalo = round(intervalo * facilidad)

    nueva_facilidad = facilidad + (0.1 - (5 - calidad) * (0.08 + (5 - calidad) * 0.02))
    nueva_facilidad = max(1.3, nueva_facilidad)  

    return nueva_facilidad, nuevo_intervalo, nuevas_repeticiones


CALIDAD_POR_BOTON = {
    "otra_vez": 0,
    "dificil": 3,
    "bien": 4,
    "facil": 5,
}

def registrar_repaso(usuario_id, flashcard_id, boton: str) -> dict:
    """
    Aplica el resultado de un repaso (uno de los botones en
    CALIDAD_POR_BOTON) a una flashcard: recalcula facilidad/intervalo con
    SM-2 y actualiza cuándo le toca el próximo repaso.

    Devuelve un dict con el nuevo estado {facilidad, intervalo,
    repeticiones, proxima_revision} o None si la flashcard no existe o el
    botón no es válido.
    """
    if boton not in CALIDAD_POR_BOTON:
        return None
    calidad = CALIDAD_POR_BOTON[boton]

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT facilidad, intervalo, repeticiones FROM flashcards WHERE id = ? AND usuario_id = ?",
        (flashcard_id, usuario_id)
    )
    fila = cursor.fetchone()
    if not fila:
        conn.close()
        return None

    nueva_facilidad, nuevo_intervalo, nuevas_repeticiones = calcular_sm2(
        fila["facilidad"], fila["intervalo"], fila["repeticiones"], calidad
    )
    hoy = date.today()
    proxima = (hoy + timedelta(days=nuevo_intervalo)).isoformat()

    cursor.execute(
        """UPDATE flashcards
           SET facilidad = ?, intervalo = ?, repeticiones = ?,
               proxima_revision = ?, ultima_revision = ?
           WHERE id = ? AND usuario_id = ?""",
        (nueva_facilidad, nuevo_intervalo, nuevas_repeticiones, proxima, hoy.isoformat(), flashcard_id, usuario_id)
    )
    conn.commit()
    conn.close()

    return {
        "facilidad": nueva_facilidad, "intervalo": nuevo_intervalo,
        "repeticiones": nuevas_repeticiones, "proxima_revision": proxima,
    }