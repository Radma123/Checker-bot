# Используем официальный образ Python
FROM python:3.10-slim

# Устанавливаем необходимые пакеты для работы с Selenium и Xvfb
RUN apt-get update && apt-get install -y \
    chromium-driver \
    chromium \
    xvfb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем requirements, если файл существует, для установки зависимостей
COPY requirements.txt requirements.txt

# Устанавливаем необходимые зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта, кроме тех, что указаны в .dockerignore
COPY . .

# Переменные окружения для работы с Selenium
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1

# Команда для запуска бота с Xvfb
CMD ["sh", "-c", "Xvfb :99 -screen 0 1920x1080x24 & python main.py"]
