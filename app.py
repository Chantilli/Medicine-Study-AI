"""
Punto de entrada de Medicine Study AI. Todo el código está dividido en
módulos por responsabilidad — este archivo solo importa y arranca:

  config.py           constantes, cliente Groq, modelo de embeddings
  database.py         SQLite: usuarios, chats
  rag_embeddings.py   fragmentación de PDFs + búsqueda semántica
  ocr_pdf.py          OCR para PDFs escaneados
  pubmed_search.py    PubMed + Europe PMC, ranking, nivel de evidencia
  citas_evidencia.py  citas, trazabilidad, anti-alucinación, juez de factualidad
  ui_helpers.py       tarjetas de Flet (papers, fuentes, badge de factualidad)
  historial_utils.py  recorte de historial, título de chat
  app_ui.py           la función main() de Flet (login + chat)

Correr la app normal:      python app.py
Self-test sin UI (PubMed): python app.py --test-pubmed "metformina diabetes tipo 2"
"""
import os
import sys
import time
import flet as ft

from config import UPLOAD_DIR
from database import crear_usuario
from pubmed_search import buscar_pubmed_estructurado, clasificar_evidencia
from citas_evidencia import formatear_cita_vancouver, formatear_cita_apa


if __name__ == "__main__" and "--test-pubmed" in sys.argv:
    consulta_prueba = " ".join(sys.argv[2:]) or "metformina diabetes tipo 2"
    usuario_test, _ = crear_usuario(f"_test_{int(time.time())}", "test1234")
    print(f"Consulta: {consulta_prueba!r}\n")

    papers_1, n_nuevos_1, total_1, debug_1, estado_1 = buscar_pubmed_estructurado(consulta_prueba, usuario_test)
    print(f"1ª búsqueda: {len(papers_1)} papers relevantes ({n_nuevos_1} nuevos) · {total_1} únicos")
    print(f"   Estado: {estado_1}")
    print(f"   Intentos: {debug_1}\n")
    for i, p in enumerate(papers_1, start=1):
        score = p.get("score")
        relevancia = f" (score {score:.2f})" if score is not None else " (sin modelo de embeddings)"
        print(f"[{i}]{relevancia} {p.get('titulo')}")
        print(f"    Nivel de evidencia: {clasificar_evidencia(p.get('tipos_publicacion', []))}")
        print(f"    Vancouver: {formatear_cita_vancouver(p)}")
        print(f"    APA:       {formatear_cita_apa(p)}")
        print()


    papers_2, n_nuevos_2, total_2, debug_2, estado_2 = buscar_pubmed_estructurado(consulta_prueba, usuario_test)
    print(f"2ª búsqueda (dedup): {len(papers_2)} papers relevantes ({n_nuevos_2} nuevos) · {total_2} únicos")
    if n_nuevos_2 == 0 and len(papers_2) > 0:
        print("✅ Dedup OK: no se insertaron filas nuevas, pero el modelo sigue recibiendo los papers como contexto.")
    elif n_nuevos_2 > 0:
        print("⚠️ Dedup no funcionó: la segunda pasada insertó papers nuevos.")
    else:
        print("⚠️ La segunda pasada se quedó sin papers relevantes (revisar ranking_semantico/umbral).")
    raise SystemExit(0)

def run_web():
    from app_ui import main

    if not os.environ.get("FLET_SECRET_KEY"):
        import secrets
        os.environ["FLET_SECRET_KEY"] = secrets.token_hex(32)

    puerto = int(os.environ.get("PORT", 7860))
    # Flet 0.28 exposed the launcher as ``app``; current releases use
    # ``run``. Keep the fallback so local and hosted environments stay
    # compatible while preserving the same web configuration.
    lanzador_legacy = getattr(ft, "app", None)
    if lanzador_legacy:
        lanzador_legacy(
            target=main,
            view=ft.AppView.WEB_BROWSER,
            host="0.0.0.0",
            port=puerto,
            upload_dir=str(UPLOAD_DIR),
        )
    else:
        ft.run(
            main,
            view=ft.AppView.WEB_BROWSER,
            host="0.0.0.0",
            port=puerto,
            upload_dir=str(UPLOAD_DIR),
        )


def run_qt():
    os.environ.setdefault("APP_UI_MODE", "qt")
    from PySide6.QtWidgets import QApplication
    from app_ui import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Medicine Study AI")
    ventana = MainWindow()
    ventana.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    modo = os.environ.get("APP_UI_MODE", "web").strip().lower()
    if modo == "qt":
        run_qt()
    elif modo in {"web", "flet"}:
        run_web()
    else:
        raise SystemExit(
            f"APP_UI_MODE no válido: {modo!r}. Usa 'web' (Space) o 'qt' (local)."
        )
