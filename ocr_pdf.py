"""
OCR para PDFs escaneados. pymupdf y rapidocr_onnxruntime se importan de
forma perezosa (solo si hace falta OCR de verdad) para no exigirlos como
dependencia dura si alguien corre esto sin esas librerías instaladas.
"""
import os
import pypdf


UMBRAL_PAGINA_OCR = 30   
DPI_OCR = 150             
MAX_PAGINAS_OCR = 30      

_OCR_CACHE = {"fitz": None, "motor": None, "intentado": False}

def _disponible_ocr() -> bool:
    """True si pymupdf y rapidocr_onnxruntime están instalados y cargaron bien."""
    if os.environ.get("OCR_DESACTIVADO") == "1":
        return False
    if not _OCR_CACHE["intentado"]:
        _OCR_CACHE["intentado"] = True
        try:
            import fitz  # PyMuPDF
            from rapidocr_onnxruntime import RapidOCR
            _OCR_CACHE["fitz"] = fitz
            _OCR_CACHE["motor"] = RapidOCR()
        except Exception:
            pass
    return _OCR_CACHE["fitz"] is not None

def _renderizar_pagina_png(doc, indice: int, dpi: int = DPI_OCR) -> bytes:
    """Renderiza una página de un documento PyMuPDF a PNG (bytes)."""
    fitz = _OCR_CACHE["fitz"]
    pagina = doc.load_page(indice)
    zoom = dpi / 72.0
    matriz = fitz.Matrix(zoom, zoom)
    pixmap = pagina.get_pixmap(matrix=matriz)
    return pixmap.tobytes("png")

def _ocr_pagina_png(datos_png: bytes) -> str:
    """Aplica OCR a una imagen PNG. Nunca lanza excepción: si algo falla
    devuelve texto vacío y esa página simplemente queda sin texto."""
    motor = _OCR_CACHE.get("motor")
    if motor is None:
        return ""
    try:
        resultado = motor(datos_png)
        
        if isinstance(resultado, tuple):
            resultado = resultado[0]
        if not resultado:
            return ""
        lineas = []
        for item in resultado:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                texto = item[1] if isinstance(item[1], str) else str(item[1])
                lineas.append(texto)
        return "\n".join(lineas)
    except Exception:
        return ""

def extraer_texto_pdf_con_ocr(ruta_pdf) -> dict:
    """
    Extrae el texto de un PDF con la estrategia de dos pasadas:
      1. Extracción normal con pypdf (rápida, funciona en PDFs "de texto").
      2. Para las páginas que salieron casi vacías (menos de
         UMBRAL_PAGINA_OCR caracteres — típico de un PDF escaneado como
         imagen), se renderiza esa página como PNG y se le aplica OCR.

    Devuelve {"texto": str, "via_ocr": bool, "paginas_ocreadas": [1-index],
    "n_paginas": int}. Si las librerías de OCR no están disponibles, se
    devuelve solo el resultado de la extracción normal (comportamiento
    idéntico al de antes de esta fase).
    """
    texto_por_pagina = []
    lector = pypdf.PdfReader(str(ruta_pdf))
    n_paginas = len(lector.pages)
    for pagina in lector.pages:
        try:
            texto_por_pagina.append(pagina.extract_text() or "")
        except Exception:
            texto_por_pagina.append("")

    if not _disponible_ocr():
        return {
            "texto": "\n\n".join(t for t in texto_por_pagina if t.strip()),
            "via_ocr": False, "paginas_ocreadas": [], "n_paginas": n_paginas,
        }

    paginas_a_ocrear = [
        i for i, t in enumerate(texto_por_pagina) if len(t.strip()) < UMBRAL_PAGINA_OCR
    ][:MAX_PAGINAS_OCR]

    paginas_ocreadas = []
    if paginas_a_ocrear:
        fitz = _OCR_CACHE["fitz"]
        doc = fitz.open(str(ruta_pdf))
        try:
            for i in paginas_a_ocrear:
                try:
                    png = _renderizar_pagina_png(doc, i, DPI_OCR)
                    texto_ocr = _ocr_pagina_png(png)
                    if texto_ocr.strip():
                        texto_por_pagina[i] = texto_ocr
                        paginas_ocreadas.append(i + 1)  
                except Exception:
                    continue
        finally:
            doc.close()

    return {
        "texto": "\n\n".join(t for t in texto_por_pagina if t.strip()),
        "via_ocr": bool(paginas_ocreadas),
        "paginas_ocreadas": paginas_ocreadas,
        "n_paginas": n_paginas,
    }


