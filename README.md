# RexTube - Видео хостинг на Django

Полнофункциональный видео-хостинг, построенный на Django 5.x с использованием HTMX для динамических взаимодействий.

## 🚀 Особенности

- **Современный дизайн**: Адаптивный интерфейс с поддержкой темной/светлой темы
- **HTMX интеграция**: Динамические взаимодействия без JavaScript фреймворков
- **Асинхронная обработка**: Celery для обработки видео и генерации превью
- **Масштабируемость**: Оптимизированные запросы и кэширование
- **Безопасность**: CSRF защита, валидация форм, защита от XSS
- **Локализация**: Поддержка нескольких языков

## 📁 Структура проекта

```
RexTube/
├── config/                          # Основная конфигурация
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/                           # Приложения Django
│   ├── core/                       # Базовое приложение
│   ├── users/                      # Управление пользователями
│   ├── videos/                     # Управление видео
│   └── comments/                   # Комментарии
├── templates/                      # HTML шаблоны
├── static/                         # Статические файлы
├── media/                          # Медиа файлы
├── requirements/                   # Зависимости
└── docs/                          # Документация
```

## 🛠 Установка

### 1. Клонирование репозитория

```bash
git clone https://github.com/AlmiroN-code/TuboCMSv3.git
cd TuboCMSv3
```

### 2. Создание виртуального окружения

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

### 3. Установка зависимостей

```bash
pip install -r requirements/development.txt
```

### 4. Настройка окружения

```bash
cp env.example .env
```

Отредактируйте `.env` файл с вашими настройками:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=rextube
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
```

### 5. Настройка базы данных

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. Сборка статических файлов

```bash
python manage.py collectstatic
```

### 7. Запуск сервера

```bash
python manage.py runserver 8008
```

Проект будет доступен по адресу: http://localhost:8008

## 🔧 Настройка Celery

### 1. Установка Redis

```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Windows
# Скачайте Redis с официального сайта
```

### 2. Запуск Celery Worker

```bash
celery -A config worker -l info
```

### 3. Запуск Celery Beat (для периодических задач)

```bash
celery -A config beat -l info
```

## 📱 Основные функции

### Для пользователей
- Регистрация и авторизация
- Загрузка видео с прогресс-баром
- Просмотр видео с HTML5 плеером
- Поиск и фильтрация видео
- Комментирование (до 2 уровней вложенности)
- Лайки/дизлайки
- Подписки на каналы
- Персональные рекомендации

### Для администраторов
- Управление пользователями
- Модерация контента
- Аналитика просмотров
- Управление категориями и тегами

## 🎨 Дизайн

Проект использует чистый CSS без фреймворков, основанный на дизайне из `example.txt`:

- **Адаптивная сетка**: Автоматическое изменение количества колонок
- **Темная/светлая тема**: Переключение через localStorage
- **Современный UI**: Градиенты, тени, плавные переходы
- **Мобильная оптимизация**: Скрытие сайдбара на мобильных устройствах

## 🔒 Безопасность

- CSRF защита для всех форм
- Валидация загружаемых файлов
- Ограничение размера файлов
- Защита от XSS в комментариях
- Rate limiting для API endpoints

## 📊 Производительность

- Оптимизированные запросы с `select_related` и `prefetch_related`
- Кэширование популярных видео
- Ленивая загрузка изображений
- Минификация статики в продакшене
- CDN для медиа файлов

## 🧪 Тестирование

```bash
# Запуск тестов
pytest

# С покрытием
pytest --cov=apps

# Только модели
pytest apps/*/tests/test_models.py
```

## 📈 Мониторинг

В продакшене настроен мониторинг через:
- Sentry для отслеживания ошибок
- Django Silk для профилирования
- Логирование в файлы

## 🚀 Развертывание

### 1. Настройка продакшена

```bash
export DJANGO_SETTINGS_MODULE=config.settings.production
```

### 2. Сборка статики

```bash
python manage.py collectstatic --noinput
```

### 3. Запуск с Gunicorn

```bash
gunicorn config.wsgi:application
```

### 4. Настройка Nginx

Пример конфигурации для Nginx:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location /static/ {
        alias /path/to/TubeCMS/staticfiles/;
    }
    
    location /media/ {
        alias /path/to/TubeCMS/media/;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📚 API

Проект предоставляет REST API для:
- Получения списка видео
- Загрузки видео
- Управления комментариями
- Поиска

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Внесите изменения
4. Добавьте тесты
5. Создайте Pull Request

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для подробностей.

## 📞 Поддержка

Если у вас есть вопросы или проблемы:
- Создайте Issue в GitHub
- Напишите в Telegram: @your_username
- Email: support@tubocms.com

## 🔄 Обновления

Следите за обновлениями в разделе [Releases](https://github.com/your-username/TubeCMS/releases).

---

**TubeCMS** - Современный видео-хостинг на Django и HTMX 🎥
