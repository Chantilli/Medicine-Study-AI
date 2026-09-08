"""
Integración con la API de Terminología ICD-11 de la OMS.

Resuelve el problema que motivó esto: traducir del inglés con el modelo
de lenguaje no es lo mismo que tener la terminología clínica correcta en
el idioma destino. Casos como "intoxicado" (envenenado, no borracho) o
anglicismos como "stent"/"bypass" que no se traducen literalmente son
justo el tipo de error que una traducción automática puede cometer.

ICD-11 es gratuita, de la OMS, y ya viene traducida oficialmente —
revisada por médicos de cada país, no traducción automática. Este
módulo busca un término y devuelve el título oficial + código en el
idioma pedido, usando el header Accept-Language de la propia API (la
OMS entrega el contenido ya traducido, no hay que traducirlo nosotros).

Requiere dos variables de entorno (secrets en HF):
    ICD11_CLIENT_ID
    ICD11_CLIENT_SECRET
Regístralas en https://icd.who.int/icdapi

Uso típico:
    from icd11_terminologia import buscar_termino_icd11
    resultado = buscar_termino_icd11("diabetes", idioma="es")
    if resultado["disponible"]:
        for r in resultado["resultados"]:
            print(r["codigo"], r["titulo"])
"""
import os
import re
import time

import requests

TOKEN_URL = "https://icdaccessmanagement.who.int/connect/token"
SEARCH_URL = "https://id.who.int/icd/release/11/2024-01/mms/search"

_IDIOMA_A_ACCEPT_LANGUAGE = {"es": "es", "en": "en", "fr": "fr", "de": "de", "zh": "zh"}

_PATRON_HTML = re.compile(r"<[^>]+>")

def _limpiar_html(texto: str) -> str:
    if not texto:
        return ""
    return _PATRON_HTML.sub("", texto).strip()


_cache_token = {"valor": None, "expira_en": 0.0}


def _obtener_token() -> str | None:
    """
    Pide (o reutiliza) el token de acceso vía OAuth2 client_credentials.
    Nunca lanza excepción: sin credenciales configuradas, sin conexión,
    o cualquier error de la OMS devuelve None — el llamador decide cómo
    seguir (normalmente: mostrar el resultado sin el glosario ICD-11 en
    vez de romper el chat).
    """
    ahora = time.time()
    if _cache_token["valor"] and ahora < _cache_token["expira_en"] - 60:
        return _cache_token["valor"]

    client_id = os.environ.get("ICD11_CLIENT_ID")
    client_secret = os.environ.get("ICD11_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None

    try:
        respuesta = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "icdapi_access",
            },
            timeout=15,
        )
        if respuesta.status_code != 200:
            return None
        datos = respuesta.json()
        token = datos.get("access_token")
        if not token:
            return None
        _cache_token["valor"] = token
        _cache_token["expira_en"] = ahora + float(datos.get("expires_in", 3600))
        return token
    except Exception:
        return None


def buscar_termino_icd11(termino: str, idioma: str = "es", top_k: int = 5) -> dict:
    """
    Busca un término médico en la terminología oficial de ICD-11, en el
    idioma pedido. Devuelve:
      {"disponible": True, "resultados": [...], "error": None} o
      {"disponible": False, "resultados": [], "error": "mensaje"}

    Cada resultado en 'resultados':
      {"titulo": str, "codigo": str, "uri": str, "score": float}
    ordenados de más a menos relevante (así los devuelve la API).

    Nunca lanza excepción — cualquier fallo (sin credenciales, sin
    conexión, respuesta rara de la OMS) se refleja en 'error' con
    disponible=False, para que el llamador pueda seguir sin el glosario
    en vez de que se caiga el resto de la respuesta.
    """
    if not termino or not termino.strip():
        return {"disponible": False, "resultados": [], "error": "Falta el término a buscar."}

    token = _obtener_token()
    if not token:
        return {
            "disponible": False, "resultados": [],
            "error": "No se pudo obtener el token de ICD-11 (revisa ICD11_CLIENT_ID / ICD11_CLIENT_SECRET).",
        }

    accept_language = _IDIOMA_A_ACCEPT_LANGUAGE.get(idioma, "en")
    try:
        respuesta = requests.get(
            SEARCH_URL,
            params={"q": termino},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Accept-Language": accept_language,
                "API-Version": "v2",
            },
            timeout=15,
        )
    except Exception as ex:
        return {"disponible": False, "resultados": [], "error": f"Error de conexión: {ex}"}

    if respuesta.status_code != 200:
        return {"disponible": False, "resultados": [], "error": f"La API de ICD-11 devolvió HTTP {respuesta.status_code}."}

    try:
        datos = respuesta.json()
    except Exception:
        return {"disponible": False, "resultados": [], "error": "La respuesta de ICD-11 no es JSON válido."}

    if datos.get("error"):
        return {
            "disponible": False, "resultados": [],
            "error": datos.get("errorMessage") or "Error desconocido de la API de ICD-11.",
        }

    entidades = datos.get("destinationEntities") or []
    resultados = []
    for ent in entidades[:top_k]:
        resultados.append({
            "titulo": _limpiar_html(ent.get("title", "")),
            "codigo": ent.get("theCode", ""),
            "uri": ent.get("id", ""),
            "score": ent.get("score", 0.0),
        })

    return {"disponible": True, "resultados": resultados, "error": None}


def _extraer_terminos_medicos(pregunta: str) -> list:
    """
    Le pide al modelo auxiliar (rápido y barato, el mismo que genera
    títulos de chat) que identifique hasta 3 términos de diagnóstico o
    condición médica en la pregunta del estudiante, EN INGLÉS — el
    índice de búsqueda de ICD-11 funciona en inglés, igual que el
    rewriter de queries de PubMed.

    Nunca lanza excepción: sin Groq configurado, sin términos médicos
    identificables (preguntas puramente conceptuales, ej. "explica la
    glucólisis"), o cualquier error de formato en la respuesta, devuelve
    una lista vacía — el llamador simplemente no arma glosario ese turno.
    """
    from config import client, MODELO_AUXILIAR
    import json as _json

    if not client or not pregunta or not pregunta.strip():
        return []
    try:
        respuesta = client.chat.completions.create(
            model=MODELO_AUXILIAR,
            messages=[
                {"role": "system", "content": (
                    "Identifica hasta 3 términos de diagnóstico o condición médica "
                    "mencionados o implicados en la pregunta del estudiante, en INGLÉS "
                    "(se van a buscar en la terminología oficial ICD-11). Si la pregunta "
                    "no menciona ninguna condición médica específica (es puramente "
                    "conceptual o de mecanismo, ej. 'explica la glucólisis', 'qué es un "
                    "receptor beta-adrenérgico'), devuelve una lista vacía — no inventes "
                    "una condición solo por rellenar. "
                    "Devuelve EXCLUSIVAMENTE un array JSON de strings, sin texto antes ni "
                    'después, sin markdown:\n["term1", "term2"]'
                )},
                {"role": "user", "content": pregunta[:500]},
            ],
            max_tokens=60,
            temperature=0.1,
        )
        contenido = (respuesta.choices[0].message.content or "").strip()
        inicio = contenido.find("[")
        fin = contenido.rfind("]") + 1
        if inicio == -1 or fin <= inicio:
            return []
        terminos = _json.loads(contenido[inicio:fin])
        if not isinstance(terminos, list):
            return []
        return [str(t).strip() for t in terminos if str(t).strip()][:3]
    except Exception:
        return []


def construir_glosario_icd11(pregunta: str, idioma: str = "es") -> dict:
    """
    Pipeline completo: extrae términos médicos de la pregunta del
    estudiante, los busca en ICD-11 en el idioma pedido, y arma un
    bloque de contexto listo para inyectar en el prompt del modelo —
    más la lista de términos encontrados, para mostrarle al estudiante
    qué se verificó (transparencia, mismo principio que el panel de
    Fuentes con los papers de PubMed).

    Devuelve {"bloque_contexto": str, "terminos_encontrados": [...]}.
    bloque_contexto es "" (y terminos_encontrados []) cuando:
      - idioma es "en" (PubMed ya está en inglés, no hace falta glosario)
      - no se identificó ningún término médico en la pregunta
      - ICD-11 no está disponible (sin credenciales, sin conexión, etc.)
    Nunca lanza excepción — un fallo aquí nunca debe romper el resto del
    turno de chat, simplemente se sigue sin el glosario.
    """
    if idioma == "en":
        return {"bloque_contexto": "", "terminos_encontrados": []}

    terminos = _extraer_terminos_medicos(pregunta)
    if not terminos:
        return {"bloque_contexto": "", "terminos_encontrados": []}

    lineas = []
    encontrados = []
    for termino in terminos:
        resultado = buscar_termino_icd11(termino, idioma=idioma, top_k=1)
        if resultado["disponible"] and resultado["resultados"]:
            top = resultado["resultados"][0]
            if not top["titulo"]:
                continue
            lineas.append(f"- {termino} \u2192 \"{top['titulo']}\" (ICD-11 {top['codigo']})")
            encontrados.append({
                "termino_buscado": termino, "titulo_oficial": top["titulo"], "codigo": top["codigo"],
            })

    if not lineas:
        return {"bloque_contexto": "", "terminos_encontrados": []}

    bloque = (
        "[GLOSARIO DE TERMINOLOGÍA OFICIAL ICD-11 — usa estos términos EXACTOS, "
        "traducidos oficialmente por la OMS y revisados por médicos, en vez de "
        "traducir tú mismo estos conceptos del inglés (evita falsos amigos y "
        "traducciones automáticas incorrectas)]:\n" + "\n".join(lineas)
    )
    return {"bloque_contexto": bloque, "terminos_encontrados": encontrados}
