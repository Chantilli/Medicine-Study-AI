"""
Recorte de historial de conversación (para no exceder el contexto del
modelo) y generación de título corto del chat con IA.
"""
from config import client, MAX_PARES_CONVERSACION, MAX_CHARS_HISTORIAL, MODELO_AUXILIAR


def recortar_historial(historial):
    """
    Mantiene el system prompt siempre presente y recorta el resto del
    historial tanto por número de pares de mensajes como por caracteres
    totales, usando las constantes MAX_PARES_CONVERSACION y
    MAX_CHARS_HISTORIAL definidas arriba.
    """
    if not historial:
        return historial

    sistema = historial[0]
    resto = historial[1:]

    max_mensajes = MAX_PARES_CONVERSACION * 2
    if len(resto) > max_mensajes:
        resto = resto[-max_mensajes:]

    total_chars = sum(len(m.get("content", "")) for m in resto)
    while total_chars > MAX_CHARS_HISTORIAL and len(resto) > 2:
        eliminado = resto.pop(0)
        total_chars -= len(eliminado.get("content", ""))

    return [sistema] + resto


_INSTRUCCION_TITULO_POR_IDIOMA = {
    "es": "Genera un título ultracorto, de máximo 3 o 4 palabras, en español sin comillas. Devuelve SOLO el título.",
    "en": "Generate an ultra-short title, at most 3 or 4 words, in English, without quotes. Return ONLY the title.",
    "fr": "Génère un titre ultra-court, de 3 ou 4 mots maximum, en français, sans guillemets. Retourne UNIQUEMENT le titre.",
    "de": "Erstelle einen ultrakurzen Titel, maximal 3 oder 4 Wörter, auf Deutsch, ohne Anführungszeichen. Gib NUR den Titel zurück.",
    "zh": "生成一个极简短的标题，最多3到4个字，用中文，不要加引号。只返回标题本身。",
}
_TITULO_POR_DEFECTO_POR_IDIOMA = {
    "es": "Consulta Médica", "en": "Medical Query", "fr": "Consultation Médicale",
    "de": "Medizinische Anfrage", "zh": "医学咨询",
}


def generar_titulo_con_ia(user_msg: str, idioma: str = "es") -> str:
    titulo_por_defecto = _TITULO_POR_DEFECTO_POR_IDIOMA.get(idioma, _TITULO_POR_DEFECTO_POR_IDIOMA["es"])
    if not client:
        return titulo_por_defecto
    instruccion = _INSTRUCCION_TITULO_POR_IDIOMA.get(idioma, _INSTRUCCION_TITULO_POR_IDIOMA["es"])
    try:
        response = client.chat.completions.create(
            model=MODELO_AUXILIAR,
            messages=[
                {"role": "system", "content": instruccion},
                {"role": "user", "content": user_msg}
            ],
            max_tokens=8, temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return titulo_por_defecto

# =====================================================================