"""
Feedback de respuestas (👍/👎) — Fase 11.

Recomendación externa que motivó esto: "Un 👍/👎 que guarde el caso.
Con 50+ casos tienes un dataset de errores propio."

A diferencia de auditoria.py (que solo guarda un hash de la consulta,
nunca el texto en claro — ver su propio docstring de política de
datos), aquí SÍ se guarda pregunta y respuesta completas a propósito:
ese es justo el punto — poder revisar después casos concretos donde el
estudiante marcó la respuesta como mala (o buena), para encontrar
patrones de error reales en vez de solo "se ve bien".

Política de datos, explícita como en auditoria.py:
  qué se guarda    -> pregunta y respuesta completas, fuentes citadas,
                      idioma, y la valoración (👍/👎) — SOLO cuando el
                      estudiante toca el botón explícitamente, nunca
                      automático
  por cuánto tiempo -> indefinido por ahora (tabla pequeña, pensada
                      para que el propio desarrollador la revise
                      manualmente, no para servir a un dashboard)
  quién accede     -> nadie desde la UI todavía (no hay panel); las
                      funciones de este módulo están listas para un
                      script de revisión o notebook, no expuestas a
                      otros estudiantes
"""
import json
import sqlite3
from datetime import datetime, timedelta

from database import DB_PATH


def registrar_feedback(usuario_id, chat_id, pregunta: str, respuesta: str,
                        valoracion: int, fuentes: list = None, idioma: str = "es") -> bool:
    """
    Guarda un voto de feedback. valoracion debe ser 1 (👍) o -1 (👎) —
    cualquier otro valor se ignora sin guardar nada. Nunca lanza
    excepción: un fallo al guardar feedback no debe romper la
    experiencia de chat del estudiante. Devuelve True si se guardó.
    """
    if valoracion not in (1, -1):
        return False
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO feedback_respuestas
               (usuario_id, chat_id, pregunta, respuesta, fuentes_json, valoracion, idioma)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                usuario_id, chat_id, pregunta, respuesta,
                json.dumps(fuentes, ensure_ascii=False) if fuentes else None,
                valoracion, idioma,
            )
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def obtener_casos_negativos(limite: int = 50) -> list:
    """
    Devuelve los últimos casos marcados con 👎 — el "dataset de
    errores" que menciona la recomendación externa: preguntas donde el
    estudiante indicó que la respuesta no sirvió, para revisar
    patrones (¿falló siempre en el mismo tema? ¿siempre sin fuentes
    citadas? etc.). Cada fila incluye 'fuentes_json' ya como string;
    usa json.loads() si necesitas la lista de fuentes estructurada.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM feedback_respuestas WHERE valoracion = -1 ORDER BY fecha DESC LIMIT ?",
        (limite,)
    )
    filas = [dict(f) for f in cursor.fetchall()]
    conn.close()
    return filas


def obtener_casos_positivos(limite: int = 50) -> list:
    """Igual que obtener_casos_negativos() pero para 👍 — útil para ver
    qué tipo de preguntas la app resuelve mejor, no solo qué falla."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM feedback_respuestas WHERE valoracion = 1 ORDER BY fecha DESC LIMIT ?",
        (limite,)
    )
    filas = [dict(f) for f in cursor.fetchall()]
    conn.close()
    return filas


def resumen_feedback(dias: int = 30) -> dict:
    """
    Conteo simple de 👍 vs 👎 en los últimos `dias` días — un vistazo
    rápido de qué tan satisfechos están los estudiantes con las
    respuestas, sin tener que abrir cada caso uno por uno.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    desde = (datetime.now() - timedelta(days=dias)).isoformat(sep=" ")
    cursor.execute(
        "SELECT valoracion, COUNT(*) FROM feedback_respuestas WHERE fecha >= ? GROUP BY valoracion",
        (desde,)
    )
    conteos = dict(cursor.fetchall())
    conn.close()
    positivos = conteos.get(1, 0)
    negativos = conteos.get(-1, 0)
    total = positivos + negativos
    return {
        "positivos": positivos,
        "negativos": negativos,
        "total": total,
        "porcentaje_positivo": round(positivos / total * 100, 1) if total else None,
    }
