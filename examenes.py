"""
Preguntas tipo examen (Fase 4).

Genera preguntas de opción múltiple con IA a partir de un tema o de
contenido real de los PDFs del estudiante (mismo mecanismo de
flashcards.py: si hay fragmentos relevantes indexados, se usan como
fuente real; si no, el modelo genera desde su conocimiento general).

Sigue el mismo patrón defensivo que aprendimos con flashcards.py: nunca
falla en silencio. generar_examen_con_ia() siempre devuelve un
diagnóstico legible cuando algo sale mal (error de red, o el modelo
devolviendo algo que no pudimos interpretar), en vez de solo decir "no
funcionó" sin explicar por qué.
"""
import json
import sqlite3

from database import DB_PATH
from config import client, MODELO_AUXILIAR


def crear_pregunta_examen(usuario_id, pregunta: str, opciones: list, respuesta_correcta: int,
                            explicacion: str = None, tema: str = None, fuente: str = None) -> int:
    """Crea una pregunta de opción múltiple. Devuelve su id."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO preguntas_examen
           (usuario_id, pregunta, opciones, respuesta_correcta, explicacion, tema, fuente)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (usuario_id, pregunta.strip(), json.dumps(opciones, ensure_ascii=False),
         respuesta_correcta, explicacion, tema, fuente)
    )
    conn.commit()
    nuevo_id = cursor.lastrowid
    conn.close()
    return nuevo_id

def obtener_preguntas_examen(usuario_id, tema: str = None) -> list:
    """
    Devuelve las preguntas de examen del usuario (más recientes primero),
    opcionalmente filtradas por tema. Cada dict trae 'opciones' ya
    deserializado como lista de Python, no como el JSON crudo guardado.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if tema:
        cursor.execute(
            "SELECT * FROM preguntas_examen WHERE usuario_id = ? AND tema = ? ORDER BY fecha_creacion DESC",
            (usuario_id, tema)
        )
    else:
        cursor.execute(
            "SELECT * FROM preguntas_examen WHERE usuario_id = ? ORDER BY fecha_creacion DESC",
            (usuario_id,)
        )
    filas = []
    for fila in cursor.fetchall():
        item = dict(fila)
        try:
            item["opciones"] = json.loads(item["opciones"])
        except Exception:
            item["opciones"] = []
        filas.append(item)
    conn.close()
    return filas

def eliminar_pregunta_examen(usuario_id, pregunta_id) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM preguntas_examen WHERE id = ? AND usuario_id = ?", (pregunta_id, usuario_id))
    conn.commit()
    conn.close()

def registrar_intento(usuario_id, pregunta_id, correcta: bool) -> None:
    """
    Guarda si el estudiante acertó o no una pregunta. No se usa todavía
    en ninguna parte de la UI — queda guardando historial para cuando
    construyamos la evaluación de nivel del alumno.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO intentos_examen (usuario_id, pregunta_id, correcta) VALUES (?, ?, ?)",
        (usuario_id, pregunta_id, 1 if correcta else 0)
    )
    conn.commit()
    conn.close()


def _parsear_json_examen(texto: str):
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

_INSTRUCCIONES_EXAMEN_POR_IDIOMA = {
    "es": (
        "Eres un asistente que genera exámenes de opción múltiple para estudiantes de medicina. A partir "
        "del texto que te den, genera EXACTAMENTE {n} preguntas de opción múltiple EN ESPAÑOL, cada una "
        "con exactamente 4 opciones (solo una correcta). Las opciones incorrectas deben ser distractores "
        "plausibles, no obviamente falsas. Incluye una explicación breve (1-2 oraciones) de por qué la "
        "respuesta correcta lo es.\n\n"
        "Devuelve EXCLUSIVAMENTE un array JSON con este formato exacto, sin texto antes ni después, sin "
        "markdown, sin explicar tu razonamiento:\n"
        '[{{"pregunta": "...", "opciones": ["...", "...", "...", "..."], '
        '"respuesta_correcta": 0, "explicacion": "..."}}, ...]\n'
        "'respuesta_correcta' es el ÍNDICE (0, 1, 2 o 3) de la opción correcta dentro de 'opciones', no "
        "el texto de la opción."
    ),
    "en": (
        "You are an assistant that generates multiple-choice exams for medical students. From the text "
        "given to you, generate EXACTLY {n} multiple-choice questions IN ENGLISH, each with exactly 4 "
        "options (only one correct). The incorrect options must be plausible distractors, not obviously "
        "false. Include a brief explanation (1-2 sentences) of why the correct answer is correct.\n\n"
        "Return ONLY a JSON array in this exact format, no text before or after, no markdown, no "
        "explaining your reasoning:\n"
        '[{{"pregunta": "...", "opciones": ["...", "...", "...", "..."], '
        '"respuesta_correcta": 0, "explicacion": "..."}}, ...]\n'
        "'respuesta_correcta' is the INDEX (0, 1, 2, or 3) of the correct option within 'opciones', not "
        "the option's text."
    ),
    "fr": (
        "Tu es un assistant qui génère des examens à choix multiples pour des étudiants en médecine. À "
        "partir du texte fourni, génère EXACTEMENT {n} questions à choix multiples EN FRANÇAIS, chacune "
        "avec exactement 4 options (une seule correcte). Les options incorrectes doivent être des "
        "distracteurs plausibles, pas manifestement fausses. Inclus une brève explication (1-2 phrases) "
        "de pourquoi la bonne réponse est correcte.\n\n"
        "Retourne UNIQUEMENT un tableau JSON dans ce format exact, sans texte avant ni après, sans "
        "markdown, sans expliquer ton raisonnement :\n"
        '[{{"pregunta": "...", "opciones": ["...", "...", "...", "..."], '
        '"respuesta_correcta": 0, "explicacion": "..."}}, ...]\n'
        "'respuesta_correcta' est l'INDEX (0, 1, 2 ou 3) de la bonne option dans 'opciones', pas le "
        "texte de l'option."
    ),
    "de": (
        "Du bist ein Assistent, der Multiple-Choice-Prüfungen für Medizinstudierende erstellt. Erstelle "
        "aus dem gegebenen Text GENAU {n} Multiple-Choice-Fragen AUF DEUTSCH, jede mit genau 4 "
        "Antwortmöglichkeiten (nur eine richtig). Die falschen Optionen müssen plausible Distraktoren "
        "sein, nicht offensichtlich falsch. Füge eine kurze Erklärung (1-2 Sätze) hinzu, warum die "
        "richtige Antwort korrekt ist.\n\n"
        "Gib AUSSCHLIESSLICH ein JSON-Array in diesem exakten Format zurück, ohne Text davor oder danach, "
        "ohne Markdown, ohne deine Überlegungen zu erklären:\n"
        '[{{"pregunta": "...", "opciones": ["...", "...", "...", "..."], '
        '"respuesta_correcta": 0, "explicacion": "..."}}, ...]\n'
        "'respuesta_correcta' ist der INDEX (0, 1, 2 oder 3) der richtigen Option innerhalb von "
        "'opciones', nicht der Text der Option."
    ),
    "zh": (
        "你是一个为医学生生成选择题考试的助手。请根据给定的文本，用中文生成正好 {n} 道选择题，"
        "每道题正好有 4 个选项（只有一个正确）。错误选项必须是合理的干扰项，不能明显错误。"
        "请附上简短的解释（1-2句话），说明为什么正确答案是正确的。\n\n"
        "只返回严格符合以下格式的 JSON 数组，前后不要有任何文字，不要用 markdown，不要解释你的推理过程：\n"
        '[{{"pregunta": "...", "opciones": ["...", "...", "...", "..."], '
        '"respuesta_correcta": 0, "explicacion": "..."}}, ...]\n'
        "'respuesta_correcta' 是 'opciones' 中正确选项的索引（0、1、2 或 3），不是选项的文字内容。"
    ),
}


def generar_examen_con_ia(usuario_id, texto_fuente: str, tema: str = None, fuente: str = None,
                            n: int = 5, idioma: str = "es"):
    """
    Le pide a Groq que genere N preguntas de opción múltiple (4 opciones
    cada una) a partir de un texto. Cada pregunta se guarda de inmediato
    en la base de datos.

    idioma: "es" (default), "en" o "fr" — igual que en
    generar_flashcards_con_ia(); un código no reconocido cae a español.

    Devuelve (lista_creadas, diagnostico) — mismo contrato que
    generar_flashcards_con_ia(): diagnostico es None si todo salió bien,
    o un string explicando qué pasó si no se pudo generar nada.
    """
    if not client:
        return [], "El cliente de Groq no está configurado (falta GROQ_API_KEY)."
    if not texto_fuente or not texto_fuente.strip():
        return [], "No había texto fuente para generar el examen."
    plantilla = _INSTRUCCIONES_EXAMEN_POR_IDIOMA.get(idioma, _INSTRUCCIONES_EXAMEN_POR_IDIOMA["es"])
    try:
        respuesta = client.chat.completions.create(
            model=MODELO_AUXILIAR,
            messages=[
                {"role": "system", "content": plantilla.format(n=n)},
                {"role": "user", "content": texto_fuente[:4000]},
            ],
            max_tokens=1800,
            temperature=0.3,
        )
        contenido = respuesta.choices[0].message.content or ""
        datos = _parsear_json_examen(contenido)
        if not isinstance(datos, list):
            preview = contenido[:300].replace("\n", " ")
            return [], f"El modelo no devolvió una lista JSON válida. Respuesta cruda: {preview!r}"

        creadas = []
        for item in datos:
            if not isinstance(item, dict):
                continue
            pregunta = (item.get("pregunta") or "").strip()
            opciones = item.get("opciones")
            indice_correcto = item.get("respuesta_correcta")
            explicacion = (item.get("explicacion") or "").strip()
            if not pregunta or not isinstance(opciones, list) or len(opciones) < 2:
                continue
            if not isinstance(indice_correcto, int) or not (0 <= indice_correcto < len(opciones)):
                continue
            opciones_limpias = [str(o).strip() for o in opciones]
            nuevo_id = crear_pregunta_examen(
                usuario_id, pregunta, opciones_limpias, indice_correcto,
                explicacion=explicacion, tema=tema, fuente=fuente
            )
            creadas.append({
                "id": nuevo_id, "pregunta": pregunta, "opciones": opciones_limpias,
                "respuesta_correcta": indice_correcto, "explicacion": explicacion,
            })
        if not creadas:
            preview = contenido[:300].replace("\n", " ")
            return [], f"El modelo devolvió una lista pero ninguna pregunta tenía el formato válido. Respuesta cruda: {preview!r}"
        return creadas, None
    except Exception as ex:
        return [], f"Error llamando a Groq: {ex}"
