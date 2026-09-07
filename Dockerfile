FROM python:3.10-slim


RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY . .



EXPOSE 7860


CMD ["flet", "run", "app.py", "--web", "--port", "7860", "--server"]
