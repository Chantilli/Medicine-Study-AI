FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libdbus-1-3 \
    libegl1 \
    libfontconfig1 \
    libgl1 \
    libglib2.0-0 \
    libice6 \
    libopengl0 \
    libsm6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb-cursor0 \
    libxcb-glx0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-shm0 \
    libxcb-sync1 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libxcb1 \
    libxi6 \
    libxkbcommon-x11-0 \
    libxkbcommon0 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /code
USER appuser

ENV PORT=7860
ENV APP_UI_MODE=web
ENV QT_QPA_PLATFORM=offscreen
EXPOSE 7860

CMD ["python", "app.py"]
