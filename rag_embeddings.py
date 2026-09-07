"""
RAG vectorial: fragmentación de PDFs, generación de embeddings y búsqueda
semántica por similitud de coseno. Usa el modelo de embeddings cargado en
config.py (una sola vez para todo el proceso) y la tabla `fragmentos` de
la base de datos (DB_PATH en database.py).
"""
import sqlite3
import numpy as np

from config import modelo_embeddings, TAMANO_FRAGMENTO, SOLAPAMIENTO_FRAGMENTO, TOP_K_FRAGMENTOS, UMBRAL_SIMILITUD_FRAGMENTOS
from database import DB_PATH


def dividir_en_fragmentos(texto: str, tamano=TAMANO_FRAGMENTO, solapamiento=SOLAPAMIENTO_FRAGMENTO):
    """
    Divide un texto largo en fragmentos más pequeños con solapamiento entre
    ellos, para que las ideas no queden cortadas justo en el límite de un
    fragmento. Cada fragmento se indexa por separado.
    """
    texto = (texto or "").strip()
    if not texto:
        return []
    fragmentos = []
    inicio = 0
    while inicio < len(texto):
        fin = inicio + tamano
        fragmentos.append(texto[inicio:fin].strip())
        inicio += max(tamano - solapamiento, 1)
    return [f for f in fragmentos if f]

def generar_embedding(texto: str):
    """Convierte un texto en un vector numérico normalizado (para que el
    producto punto entre dos vectores sea directamente su similitud de
    coseno)."""
    if not modelo_embeddings or not texto:
        return None
    vector = modelo_embeddings.encode(texto, normalize_embeddings=True)
    return np.asarray(vector, dtype=np.float32)

def guardar_fragmentos_pdf(usuario_id, nombre_fuente: str, texto_completo: str, tipo_texto: str = "normal") -> int:
    """
    Divide el texto de un PDF en fragmentos, genera su embedding y los
    guarda en la base de datos ligados al usuario_id. Devuelve cuántos
    fragmentos se guardaron. Estos fragmentos quedan disponibles para
    búsqueda semántica en cualquier chat futuro de ese usuario (no solo en
    la conversación actual).

    tipo_texto: "normal" (texto extraído directo del PDF) u "ocr" (texto
    reconocido en páginas escaneadas). Se usa solo para mostrarlo en la UI
    y en el panel de trazabilidad — no cambia cómo se busca.
    """
    if not modelo_embeddings:
        return 0
    fragmentos = dividir_en_fragmentos(texto_completo)
    if not fragmentos:
        return 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
   
    cursor.execute(
        "DELETE FROM fragmentos WHERE usuario_id = ? AND fuente = ?",
        (usuario_id, nombre_fuente)
    )
    guardados = 0
    for frag in fragmentos:
        vector = generar_embedding(frag)
        if vector is None:
            continue
        cursor.execute(
            "INSERT INTO fragmentos (usuario_id, fuente, texto, vector, tipo_texto) VALUES (?, ?, ?, ?, ?)",
            (usuario_id, nombre_fuente, frag, vector.tobytes(), tipo_texto)
        )
        guardados += 1
    conn.commit()
    conn.close()
    return guardados

def buscar_fragmentos_relevantes(usuario_id, pregunta: str, top_k=TOP_K_FRAGMENTOS, umbral=UMBRAL_SIMILITUD_FRAGMENTOS):
    """
    Búsqueda vectorial: convierte la pregunta en un embedding y la compara
    (similitud de coseno) contra todos los fragmentos de PDFs que el
    usuario ha indexado. Devuelve los top_k más relevantes por encima del
    umbral mínimo de similitud, en vez de mandar el PDF completo al modelo.

    Cada resultado es (similitud, fuente, texto, tipo_texto), donde
    tipo_texto indica si ese fragmento vino de texto normal del PDF o de
    OCR sobre una página escaneada.
    """
    if not modelo_embeddings:
        return []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT fuente, texto, vector, tipo_texto FROM fragmentos WHERE usuario_id = ?", (usuario_id,))
    filas = cursor.fetchall()
    conn.close()
    if not filas:
        return []

    vector_pregunta = generar_embedding(pregunta)
    if vector_pregunta is None:
        return []

    resultados = []
    for fuente, texto, vector_blob, tipo_texto in filas:
        vector_frag = np.frombuffer(vector_blob, dtype=np.float32)
        similitud = float(np.dot(vector_pregunta, vector_frag))
        if similitud >= umbral:
            resultados.append((similitud, fuente, texto, tipo_texto or "normal"))

    resultados.sort(key=lambda r: r[0], reverse=True)
    return resultados[:top_k]

