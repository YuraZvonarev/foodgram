# Foodgram - продуктовый помощник

## Описание проекта

Foodgram - это веб-приложение, где пользователи могут публиковать рецепты, подписываться на других авторов, добавлять рецепты в избранное и формировать список покупок.

## Установка и запуск

### Локальный запуск (без Docker)

1. Клонируйте репозиторий:
```bash
   git clone git@github.com:YuraZvonarev/foodgram.git
   cd foodgram

2.Создайте виртуальное окружение и активируйте его:
python -m venv venv
. venv/Scripts/activate

3. Установите зависимости:
pip install -r requirements.txt

4. Примените миграции, создайте суперпользователя, соберите статику:
cd backend
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic

5. Запустите сервер разработки:
python manage.py runserver

### Запуск через Docker
docker compose -f docker-compose.production.yml up -d

## Примеры запросов к API
Получение списка рецептов
GET /api/recipes/
Добваление рецепта в избранное(требуется авторизация)
POST /api/recipes/{id}/favorite/
Скачивание списка покупок
GET /api/recipes/download_shopping_cart/

## Технологии
Python 3.12
Django 4.2
Django REST Framework
PostgreSQL
Docker & Docker Compose
Gunicorn
Nginx