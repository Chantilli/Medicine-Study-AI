"""
Extracción de tablas de PDFs.

Usa pdfplumber (puro Python — a diferencia de Camelot o Tabula, no
necesita Ghostscript ni Java instalados en el contenedor) para detectar y
extraer tablas de PDFs "de texto" normales. Para tablas dentro de páginas
escaneadas (imagen) se necesitaría OCR especializado en tablas, que es un
problema bastante más difícil y queda fuera de este alcance — ese caso
sigue cubierto por el OCR de texto plano de ocr_pdf.py, solo que la
tabla perderá su estructura de filas/columnas.

Cada tabla se convierte a una representación en Markdown limpia: una
tabla de dosis o valores de laboratorio pierde toda su utilidad si se
manda como texto plano sin alinear filas y columnas, tanto para que el
LLM la lea bien como para que el modelo de embeddings la indexe de forma
coherente.
"""
import pdfplumber


def _fila_a_markdown(fila) -> str:
    celdas = [str(c).strip() if c is not None else "" for c in fila]
    return "| " + " | ".join(celdas) + " |"


def _tabla_a_markdown(tabla: list) -> str:
    """
    Convierte una tabla (lista de filas, cada fila una lista de celdas)
    a texto Markdown. La primera fila se asume encabezado.
    """
    if not tabla or not tabla[0]:
        return ""
    lineas = [_fila_a_markdown(tabla[0])]
    lineas.append("| " + " | ".join(["---"] * len(tabla[0])) + " |")
    for fila in tabla[1:]:
        lineas.append(_fila_a_markdown(fila))
    return "\n".join(lineas)


def extraer_tablas_pdf(ruta_pdf) -> list:
    """
    Extrae todas las tablas detectables de un PDF de texto (no
    escaneado). Devuelve una lista de dicts:
      {"pagina": int, "indice_en_pagina": int, "markdown": str,
       "n_filas": int, "n_columnas": int}

    Nunca lanza excepción: si pdfplumber falla, si el archivo es un PDF
    escaneado sin tablas detectables, o si algo sale mal en una página
    puntual, esa página se salta y se sigue con las demás — en el peor
    caso se devuelve una lista vacía y el resto del flujo de subida de
    PDF (extracción de texto normal / OCR) sigue funcionando igual.
    """
    tablas_encontradas = []
    try:
        with pdfplumber.open(str(ruta_pdf)) as pdf:
            for num_pagina, pagina in enumerate(pdf.pages, start=1):
                try:
                    tablas = pagina.extract_tables()
                except Exception:
                    continue
                for i, tabla in enumerate(tablas, start=1):
                    if not tabla or len(tabla) < 2:
                       
                        continue
                    markdown = _tabla_a_markdown(tabla)
                    if not markdown.strip():
                        continue
                    tablas_encontradas.append({
                        "pagina": num_pagina,
                        "indice_en_pagina": i,
                        "markdown": markdown,
                        "n_filas": len(tabla),
                        "n_columnas": len(tabla[0]) if tabla else 0,
                    })
    except Exception:
        return []
    return tablas_encontradas


def formatear_tablas_para_fragmentos(tablas: list, nombre_pdf: str) -> list:
    """
    Convierte la salida de extraer_tablas_pdf() en una lista de textos
    listos para indexar como fragmentos independientes (uno por tabla),
    con una cabecera que indica de qué página y documento vienen —
    importante para que, cuando el modelo cite el fragmento, el
    estudiante sepa exactamente dónde buscarla en el PDF original.
    """
    fragmentos = []
    for t in tablas:
        encabezado = (
            f"[Tabla {t['indice_en_pagina']} de la página {t['pagina']} "
            f"de '{nombre_pdf}']\n"
        )
        fragmentos.append(encabezado + t["markdown"])
    return fragmentos
