"""
Base de datos local (SQLite): esquema, migraciones, cuentas de usuario y
CRUD de chats. DB_PATH se define aquí y lo importan los demás módulos
que también tocan la misma base (fragmentos, papers).
"""
import json
import sqlite3
from pathlib import Path
import bcrypt


DB_PATH = Path(__file__).parent / "historial_chats.db"

def inicializar_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            usuario_id INTEGER,
            titulo TEXT,
            mensajes TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fragmentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            fuente TEXT,
            texto TEXT,
            vector BLOB,
            tipo_texto TEXT DEFAULT 'normal',
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("PRAGMA table_info(fragmentos)")
    columnas_fragmentos = [fila[1] for fila in cursor.fetchall()]
    if "tipo_texto" not in columnas_fragmentos:
        cursor.execute("ALTER TABLE fragmentos ADD COLUMN tipo_texto TEXT DEFAULT 'normal'")
   
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            pmid TEXT,
            doi TEXT,
            titulo TEXT,
            autores TEXT,          -- JSON: [{apellido, iniciales}, ...]
            revista TEXT,
            anio TEXT,
            volumen TEXT,
            numero TEXT,
            paginas TEXT,
            resumen TEXT,
            tipos_publicacion TEXT, -- JSON: ["Randomized Controlled Trial", ...]
            vector BLOB,           -- embedding del título+resumen
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(usuario_id, pmid),
            UNIQUE(usuario_id, doi)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_usuario ON papers(usuario_id, fecha DESC)")
   
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            pregunta TEXT NOT NULL,
            respuesta TEXT NOT NULL,
            tema TEXT,
            fuente TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            facilidad REAL DEFAULT 2.5,
            intervalo INTEGER DEFAULT 0,
            repeticiones INTEGER DEFAULT 0,
            proxima_revision TEXT DEFAULT (date('now')),
            ultima_revision TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_flashcards_repaso ON flashcards(usuario_id, proxima_revision)")
   
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preguntas_examen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            pregunta TEXT NOT NULL,
            opciones TEXT NOT NULL,          -- JSON: ["opción A", "opción B", ...]
            respuesta_correcta INTEGER NOT NULL,  -- índice (0-based) en opciones
            explicacion TEXT,
            tema TEXT,
            fuente TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS intentos_examen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            pregunta_id INTEGER NOT NULL,
            correcta INTEGER NOT NULL,  -- 0 o 1
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conceptos_estudiados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            tema TEXT NOT NULL,
            tipo TEXT,       -- 'flashcards' o 'examen'
            fuente TEXT,
            vector BLOB,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conceptos_usuario ON conceptos_estudiados(usuario_id, fecha DESC)")
   
    cursor.execute("PRAGMA table_info(papers)")
    columnas_papers = [fila[1] for fila in cursor.fetchall()]
    if "tipos_publicacion" not in columnas_papers:
        cursor.execute("ALTER TABLE papers ADD COLUMN tipos_publicacion TEXT")

    # -----------------------------------------------------------------
    # Fase 6 (seguridad): límite de uso por usuario + auditoría de uso.
    # -----------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS solicitudes_uso (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_solicitudes_usuario_fecha ON solicitudes_uso(usuario_id, tipo, fecha)")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auditoria_uso (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            operacion TEXT NOT NULL,
            modelo TEXT,
            tokens_entrada INTEGER,
            tokens_salida INTEGER,
            estado TEXT DEFAULT 'ok',
            latencia_ms INTEGER,
            n_fuentes INTEGER,
            hash_consulta TEXT,
            longitud_consulta INTEGER,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_auditoria_usuario_fecha ON auditoria_uso(usuario_id, fecha)")

    # -----------------------------------------------------------------
    # Fase 11: feedback de respuestas (👍/👎) — a diferencia de
    # auditoria_uso, aquí SÍ se guarda el texto completo de pregunta y
    # respuesta a propósito: es un dataset de casos para que el
    # desarrollador revise patrones de error, no telemetría anónima.
    # Solo se llena cuando el estudiante toca 👍/👎 explícitamente.
    # -----------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback_respuestas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            chat_id TEXT,
            pregunta TEXT,
            respuesta TEXT,
            fuentes_json TEXT,
            valoracion INTEGER NOT NULL,
            idioma TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_valoracion_fecha ON feedback_respuestas(valoracion, fecha)")
    
    cursor.execute("PRAGMA table_info(chats)")
    columnas_existentes = [fila[1] for fila in cursor.fetchall()]
    if "usuario_id" not in columnas_existentes:
        cursor.execute("ALTER TABLE chats ADD COLUMN usuario_id INTEGER")
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verificar_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False

def crear_usuario(usuario: str, password: str):
    """Crea una cuenta nueva. Devuelve (usuario_id, error)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO usuarios (usuario, password_hash) VALUES (?, ?)",
            (usuario, hash_password(password))
        )
        conn.commit()
        return cursor.lastrowid, None
    except sqlite3.IntegrityError:
        return None, "Ese nombre de usuario ya está en uso."
    except Exception as e:
        return None, f"No se pudo crear la cuenta: {e}"
    finally:
        conn.close()

def obtener_usuario_por_nombre(usuario: str):
    """Devuelve (id, password_hash) o None si no existe."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash FROM usuarios WHERE usuario = ?", (usuario,))
    fila = cursor.fetchone()
    conn.close()
    return fila


def guardar_chat_db(chat_id, titulo, mensajes, usuario_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO chats (id, usuario_id, titulo, mensajes) VALUES (?, ?, ?, ?)",
        (chat_id, usuario_id, titulo, json.dumps(mensajes))
    )
    conn.commit()
    conn.close()

def obtener_todos_los_chats(usuario_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, titulo FROM chats WHERE usuario_id = ? ORDER BY fecha DESC",
        (usuario_id,)
    )
    filas = cursor.fetchall()
    conn.close()
    return filas

def obtener_mensajes_chat(chat_id, usuario_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT mensajes FROM chats WHERE id = ? AND usuario_id = ?",
        (chat_id, usuario_id)
    )
    fila = cursor.fetchone()
    conn.close()
    if fila:
        return json.loads(fila[0])
    return []

def eliminar_chat_db(chat_id, usuario_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM chats WHERE id = ? AND usuario_id = ?",
        (chat_id, usuario_id)
    )
    conn.commit()
    conn.close()

inicializar_db()

# =====================================================================