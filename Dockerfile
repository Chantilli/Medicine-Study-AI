# Medicine Study AI — Dockerfile para Hugging Face Spaces (SDK Docker)
#
# Estructura pensada para coincidir con lo que ya vimos correr en tu
# Space (los tracebacks mostraban rutas como /code/app_ui.py) — si ya
# tienes un Dockerfile funcionando con esa misma carpeta, compáralo con
# este antes de reemplazarlo.

FROM python:3.11-slim

# Dependencias de sistema:
#   libgl1 / libglib2.0-0  -> las necesita rapidocr_onnxruntime (usa
#                             OpenCV por debajo, y en imágenes "slim" de
#                             Debian esas dos librerías no vienen por
#                             defecto — sin ellas el OCR truena al
#                             importar, no al usarse, así que el error
#                             aparece recién en el primer PDF escaneado).
#   build-essential        -> por si algún paquete no trae wheel
#                             precompilada para esta versión de Python
#                             y necesita compilar una extensión en C.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Instalar dependencias ANTES de copiar el resto del código: mientras
# no cambies requirements.txt, Docker reusa esta capa del caché y no
# reinstala todo (sentence-transformers/torch es lo más pesado de bajar).
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Ahora sí, el resto del código del proyecto.
COPY . .

# Hugging Face Spaces corre los contenedores Docker con un usuario
# no-root (UID 1000) — sin esto, la app podría no tener permiso de
# escritura para crear historial_chats.db o guardar PDFs subidos.
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /code
USER appuser

# Los Spaces de tipo Docker esperan que la app escuche en el puerto
# 7860 por defecto — app.py YA lee esto de la variable de entorno PORT
# (puerto = int(os.environ.get("PORT", 7860))), así que no hace falta
# tocar nada del lado de Python, solo declararlo aquí.
ENV PORT=7860
EXPOSE 7860

CMD ["python", "app.py"]
