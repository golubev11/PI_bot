FROM python:3.20-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Установка Poetry
RUN pip install poetry

# Копирование файлов конфигурации Poetry
COPY pyproject.toml poetry.lock* ./

# Настройка Poetry и установка зависимостей
RUN poetry config virtualenvs.create false \
    && poetry install

COPY src/ ./src/
COPY .env* ./

CMD ["python", "-m", "src.main"]
