"""
Recorte de historial de conversación (para no exceder el contexto del
modelo) y generación de título corto del chat con IA.
"""
from config import (
    client, MAX_PARES_CONVERSACION, MAX_CHARS_HISTORIAL, MODELO_AUXILIAR,
    MAX_TOKENS_TITULO, llamar_modelo_auxiliar,
)


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


def limpiar_respuesta_para_historial(respuesta):
    """Conserva solo la respuesta visible; nunca guarda contexto de fuentes."""
    return (respuesta or "").strip()


def limpiar_pregunta_para_historial(pregunta):
    """Migra mensajes antiguos que aún contenían bloques de contexto."""
    texto = (pregunta or "").strip()
    if "Pregunta:" in texto:
        texto = texto.rsplit("Pregunta:", 1)[-1].strip()
    return texto.split("[Nota interna", 1)[0].strip()


def preparar_historial_para_guardar(historial):
    """Serializa únicamente pares pregunta/respuesta, sin metadatos ni fuentes."""
    limpio = []
    for mensaje in historial:
        rol = mensaje.get("role")
        if rol == "system":
            continue
        contenido = mensaje.get("content", "")
        if rol == "user":
            contenido = limpiar_pregunta_para_historial(contenido)
        else:
            contenido = limpiar_respuesta_para_historial(contenido)
        if contenido:
            limpio.append({"role": rol, "content": contenido})
    return limpio


def migrar_historial_guardado(historial, idioma="es"):
    """Normaliza historiales previos y vuelve a añadir solo el system prompt."""
    if not historial:
        return []
    sistema = next((m for m in historial if m.get("role") == "system"), None)
    resultado = [{"role": "system", "content": sistema.get("content", "")}] if sistema else []
    for mensaje in preparar_historial_para_guardar(historial):
        resultado.append(mensaje)
    return resultado


def construir_mensajes_con_contexto_actual(historial, pregunta, contexto_actual=""):
    """Construye el payload del modelo sin reinyectar contexto histórico."""
    mensajes = []
    historial_limpio = preparar_historial_para_guardar(historial)
    sistema = next((m for m in historial if m.get("role") == "system"), None)
    mensajes_base = ([sistema] if sistema else []) + historial_limpio
    for mensaje in recortar_historial(mensajes_base):
        if mensaje.get("role") == "system":
            mensajes.append(mensaje)
        elif mensaje.get("role") in {"user", "assistant"}:
            contenido = mensaje.get("content", "").strip()
            if contenido:
                mensajes.append({"role": mensaje["role"], "content": contenido})
    contenido_actual = pregunta.strip()
    if contexto_actual.strip():
        contenido_actual = f"{contexto_actual.strip()}\n\nPregunta: {contenido_actual}"
    mensajes.append({"role": "user", "content": contenido_actual})
    return mensajes


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
        response = llamar_modelo_auxiliar(
            "titulo_chat",
            model=MODELO_AUXILIAR,
            messages=[
                {"role": "system", "content": instruccion},
                {"role": "user", "content": user_msg}
            ],
            max_tokens=MAX_TOKENS_TITULO, temperature=0.3
        )
        titulo = (response.choices[0].message.content or "").strip()
        return titulo or titulo_por_defecto
    except Exception:
        return titulo_por_defecto
