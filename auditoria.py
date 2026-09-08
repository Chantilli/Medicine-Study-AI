"""
Auditoría de uso (Fase 6 — seguridad operativa).

Registra QUIÉN hizo QUÉ operación y CUÁNDO — útil para depurar, ver
patrones de uso, o detectar abuso — sin guardar el contenido médico
potencially sensible de la consulta. En vez del texto de la pregunta se
guarda su longitud y un hash SHA-256: sirve para, por ejemplo, notar
que la misma pregunta se repitió muchas veces, sin que quede legible en
la base de datos qué preguntó el estudiante.

Política de datos (para que quede explícita, no implícita):
  qué se guarda   -> usuario_id, operación, modelo, tokens, estado,
                     latencia, nº de fuentes, hash+longitud de la
                     consulta (NUNCA el texto en claro)
  por cuánto tiempo -> indefinido por ahora (tabla pequeña); si esto
                     crece, lo natural es podar filas con más de N
                     meses igual que se hace con solicitudes_uso
  quién accede    -> por ahora, nadie desde la UI (no hay panel de
                     administración todavía) — obtener_resumen_auditoria()
                     ya está lista para conectarse a una vista de admin
                     cuando se necesite
"""
import hashlib
import sqlite3
from datetime import datetime, timedelta

from database import DB_PATH


def _hash_consulta(texto: str):
    if not texto:
        return None
    return hashlib.sha256(texto.strip().encode("utf-8")).hexdigest()[:16]


def registrar_evento(usuario_id, operacion: str, modelo: str = None,
                      tokens_entrada: int = None, tokens_salida: int = None,
                      estado: str = "ok", latencia_ms: int = None,
                      n_fuentes: int = None, texto_consulta: str = None) -> None:
    """
    Inserta una fila de auditoría. Nunca lanza excepción — un fallo al
    auditar no debe tumbar la operación real que se está auditando (por
    eso todo el cuerpo va en un try/except silencioso).
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO auditoria_uso
               (usuario_id, operacion, modelo, tokens_entrada, tokens_salida,
                estado, latencia_ms, n_fuentes, hash_consulta, longitud_consulta)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (usuario_id, operacion, modelo, tokens_entrada, tokens_salida,
             estado, latencia_ms, n_fuentes, _hash_consulta(texto_consulta),
             len(texto_consulta) if texto_consulta else None)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def obtener_resumen_auditoria(usuario_id=None, dias: int = 7) -> list:
    """
    Resumen agregado por operación en los últimos `dias` días —
    conteo, latencia promedio y tokens totales. Si usuario_id es None,
    agrega de TODOS los usuarios (vista de administración). Todavía no
    hay una pantalla en la UI que llame a esto, pero queda lista para
    cuando haga falta un panel de uso.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    desde = (datetime.now() - timedelta(days=dias)).isoformat(sep=" ")

    if usuario_id is not None:
        cursor.execute(
            """SELECT operacion, COUNT(*) AS n, AVG(latencia_ms) AS latencia_prom,
                      SUM(COALESCE(tokens_entrada, 0) + COALESCE(tokens_salida, 0)) AS tokens_total,
                      SUM(CASE WHEN estado != 'ok' THEN 1 ELSE 0 END) AS n_errores
               FROM auditoria_uso WHERE usuario_id = ? AND fecha >= ?
               GROUP BY operacion ORDER BY n DESC""",
            (usuario_id, desde)
        )
    else:
        cursor.execute(
            """SELECT operacion, COUNT(*) AS n, AVG(latencia_ms) AS latencia_prom,
                      SUM(COALESCE(tokens_entrada, 0) + COALESCE(tokens_salida, 0)) AS tokens_total,
                      SUM(CASE WHEN estado != 'ok' THEN 1 ELSE 0 END) AS n_errores
               FROM auditoria_uso WHERE fecha >= ?
               GROUP BY operacion ORDER BY n DESC""",
            (desde,)
        )
    filas = [dict(f) for f in cursor.fetchall()]
    conn.close()
    return filas
