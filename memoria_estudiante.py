"""
Memoria semántica y evaluación de nivel del estudiante (Fase 4, última
pieza).

Dos responsabilidades:

1. Memoria semántica — cada vez que el estudiante genera flashcards o un
   examen sobre un tema, queda registrado con su embedding. Así se puede
   buscar semánticamente "¿ya estudié algo parecido a esto?" (misma
   lógica de similitud de coseno que usamos para los fragmentos de PDF y
   los papers de PubMed — no es nada nuevo conceptualmente, es aplicar la
   misma herramienta a un dato distinto).

2. Evaluación de nivel — usa los intentos de examen que ya se venían
   guardando (desde la pieza anterior, sin usarse todavía) para calcular
   qué tan bien le va al estudiante en cada tema, y etiquetarlo con un
   nivel cualitativo simple.
"""
import sqlite3
from collections import defaultdict

from database import DB_PATH
from rag_embeddings import generar_embedding
import numpy as np


def registrar_concepto_estudiado(usuario_id, tema: str, tipo: str, fuente: str = None) -> None:
    """
    Registra que el estudiante estudió un tema (al generar flashcards o
    un examen sobre él). Si el modelo de embeddings no está disponible,
    igual se guarda el registro pero sin vector — solo se pierde la
    capacidad de buscarlo semánticamente después, no el registro en sí.
    """
    if not tema or not tema.strip():
        return
    vector = generar_embedding(tema)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conceptos_estudiados (usuario_id, tema, tipo, fuente, vector) VALUES (?, ?, ?, ?, ?)",
        (usuario_id, tema.strip(), tipo, fuente, vector.tobytes() if vector is not None else None)
    )
    conn.commit()
    conn.close()

def obtener_temas_relacionados(usuario_id, tema_actual: str, top_k: int = 3, umbral: float = 0.35, excluir_iguales: bool = True) -> list:
    """
    Busca, entre los temas que el estudiante ya estudió antes, los más
    parecidos semánticamente al tema_actual — para poder decirle "esto se
    relaciona con lo que ya viste el [fecha]". excluir_iguales descarta
    el tema si es literalmente el mismo texto (para no "recordarle" el
    tema que acaba de escribir ahora mismo).

    Devuelve una lista de dicts {tema, tipo, fecha, similitud}, la más
    parecida primero.
    """
    vector_actual = generar_embedding(tema_actual)
    if vector_actual is None:
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT tema, tipo, fecha, vector FROM conceptos_estudiados WHERE usuario_id = ? AND vector IS NOT NULL",
        (usuario_id,)
    )
    filas = cursor.fetchall()
    conn.close()

    resultados = []
    for fila in filas:
        if excluir_iguales and fila["tema"].strip().lower() == tema_actual.strip().lower():
            continue
        vector_fila = np.frombuffer(fila["vector"], dtype=np.float32)
        similitud = float(np.dot(vector_actual, vector_fila))
        if similitud >= umbral:
            resultados.append({
                "tema": fila["tema"], "tipo": fila["tipo"],
                "fecha": fila["fecha"], "similitud": similitud,
            })

    resultados.sort(key=lambda r: r["similitud"], reverse=True)
    return resultados[:top_k]


_UMBRAL_DOMINADO = 0.80
_UMBRAL_EN_PROGRESO = 0.50
_MIN_INTENTOS_PARA_EVALUAR = 2  

def _nivel_cualitativo(porcentaje_aciertos: float, n_intentos: int) -> str:
    if n_intentos < _MIN_INTENTOS_PARA_EVALUAR:
        return "Muy pocos datos aún"
    if porcentaje_aciertos >= _UMBRAL_DOMINADO:
        return "Dominado"
    if porcentaje_aciertos >= _UMBRAL_EN_PROGRESO:
        return "En progreso"
    return "Necesita repaso"

def evaluar_nivel_por_tema(usuario_id) -> list:
    """
    Agrupa los intentos de examen (preguntas_examen + intentos_examen)
    por tema y calcula el porcentaje de aciertos y un nivel cualitativo
    para cada uno.

    Devuelve una lista de dicts {tema, n_intentos, aciertos, porcentaje,
    nivel}, ordenada de peor a mejor desempeño (para que lo que necesita
    más repaso aparezca primero).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """SELECT COALESCE(p.tema, 'Sin tema') AS tema, i.correcta
           FROM intentos_examen i
           JOIN preguntas_examen p ON p.id = i.pregunta_id
           WHERE i.usuario_id = ?""",
        (usuario_id,)
    )
    filas = cursor.fetchall()
    conn.close()

    por_tema = defaultdict(lambda: {"n_intentos": 0, "aciertos": 0})
    for fila in filas:
        stats = por_tema[fila["tema"]]
        stats["n_intentos"] += 1
        stats["aciertos"] += fila["correcta"]

    resultado = []
    for tema, stats in por_tema.items():
        porcentaje = stats["aciertos"] / stats["n_intentos"] if stats["n_intentos"] else 0.0
        resultado.append({
            "tema": tema,
            "n_intentos": stats["n_intentos"],
            "aciertos": stats["aciertos"],
            "porcentaje": porcentaje,
            "nivel": _nivel_cualitativo(porcentaje, stats["n_intentos"]),
        })
    resultado.sort(key=lambda r: r["porcentaje"])
    return resultado

def resumen_progreso(usuario_id) -> dict:
    """
    Estadísticas generales de estudio: cuántos temas ha tocado el
    estudiante y cuántas flashcards/exámenes ha generado en total — un
    vistazo rápido de actividad, sin entrar al detalle por tema.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT tema) FROM conceptos_estudiados WHERE usuario_id = ?", (usuario_id,))
    n_temas = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM flashcards WHERE usuario_id = ?", (usuario_id,))
    n_flashcards = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM preguntas_examen WHERE usuario_id = ?", (usuario_id,))
    n_preguntas = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM intentos_examen WHERE usuario_id = ?", (usuario_id,))
    n_intentos = cursor.fetchone()[0]
    conn.close()
    return {
        "n_temas": n_temas, "n_flashcards": n_flashcards,
        "n_preguntas": n_preguntas, "n_intentos": n_intentos,
    }
