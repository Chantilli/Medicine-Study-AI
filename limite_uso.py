"""
Límite de uso por usuario (Fase 6 — seguridad operativa).

Objetivo: que una sola cuenta no pueda agotar la cuota de Groq (u otros
recursos compartidos) para el resto de los usuarios. El límite se aplica
en BACKEND —no solo deshabilitando un botón en la UI— porque un botón
deshabilitado no impide nada si alguien llama a la función directamente
o dispara el evento más rápido de lo que la UI alcanza a reaccionar.

Estrategia: ventanas deslizantes simples (conteo de filas en
solicitudes_uso dentro de los últimos N segundos), no un algoritmo de
"token bucket" sofisticado — es más que suficiente para el volumen de
una app de estudio, y es trivial de razonar/depurar.

Cada "tipo" de operación (chat, pubmed, flashcards, examen) tiene su
propio límite independiente, porque tienen costos muy distintos: una
búsqueda en PubMed pega contra una API externa (NCBI/Europe PMC) y no
solo contra Groq, así que también conviene limitarla aparte para no
tirar esa integración.
"""
import sqlite3
import time
from datetime import datetime, timedelta

from database import DB_PATH
from traducciones import t

LIMITES = {
    "chat": [(8, 60), (60, 3600), (300, 86400)],
    "pubmed": [(4, 60), (30, 3600), (100, 86400)],
    "flashcards": [(3, 60), (20, 3600), (80, 86400)],
    "examen": [(3, 60), (20, 3600), (80, 86400)],
    "icd11": [(4, 60), (30, 3600), (100, 86400)],
}

_INTERVALO_LIMPIEZA = 50
_contador_llamadas = {"n": 0}

_ETIQUETAS_VENTANA = {60: "ventana_minuto", 3600: "ventana_hora", 86400: "ventana_dia"}


def _limpiar_solicitudes_antiguas(cursor):
    """Borra solicitudes de más de 2 días — no hace falta conservarlas más
    tiempo para calcular ninguna de las ventanas de LIMITES."""
    limite_fecha = (datetime.now() - timedelta(days=2)).isoformat(sep=" ")
    cursor.execute("DELETE FROM solicitudes_uso WHERE fecha < ?", (limite_fecha,))


def registrar_solicitud(usuario_id, tipo: str) -> None:
    """Registra una solicitud del tipo dado. Llamar SOLO después de que
    verificar_limite() haya dado luz verde, justo antes de hacer la
    llamada costosa (a Groq, a PubMed, etc.) — así el límite cuenta
    intentos reales, incluyendo los que luego fallan por otra razón."""
    if usuario_id is None:
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO solicitudes_uso (usuario_id, tipo) VALUES (?, ?)",
        (usuario_id, tipo)
    )
    _contador_llamadas["n"] += 1
    if _contador_llamadas["n"] % _INTERVALO_LIMPIEZA == 0:
        _limpiar_solicitudes_antiguas(cursor)
    conn.commit()
    conn.close()


def verificar_limite(usuario_id, tipo: str, idioma: str = "es") -> dict:
    """
    Revisa si el usuario puede hacer una solicitud más del tipo dado,
    contra TODAS las ventanas configuradas para ese tipo (la más
    restrictiva gana). Devuelve:
      {"permitido": True} si puede continuar, o
      {"permitido": False, "motivo": str, "reintentar_en_segundos": int}

    Si usuario_id es None (no debería pasar con sesión iniciada) o el
    tipo no tiene límite configurado, siempre permite — nunca bloquea
    por un error de configuración.
    """
    if usuario_id is None or tipo not in LIMITES:
        return {"permitido": True}

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    ahora = datetime.now()

    for maximo, ventana_segundos in LIMITES[tipo]:
        desde = (ahora - timedelta(seconds=ventana_segundos)).isoformat(sep=" ")
        cursor.execute(
            "SELECT COUNT(*) FROM solicitudes_uso WHERE usuario_id = ? AND tipo = ? AND fecha >= ?",
            (usuario_id, tipo, desde)
        )
        total = cursor.fetchone()[0]
        if total >= maximo:
            conn.close()
            clave_etiqueta = _ETIQUETAS_VENTANA.get(ventana_segundos)
            etiqueta = t(clave_etiqueta, idioma) if clave_etiqueta else f"{ventana_segundos}s"
            return {
                "permitido": False,
                "motivo": t("limite_alcanzado", idioma, maximo=maximo, tipo=tipo, etiqueta=etiqueta),
                "reintentar_en_segundos": ventana_segundos,
            }

    conn.close()
    return {"permitido": True}
