# TubeCMS v3 - Полное руководство

**Версия:** 2.0.0  
**Дата:** 26 ноября 2025

## Содержание

1. [Быстрый старт](#быстрый-старт)
2. [Архитектура системы](#архитектура-системы)
3. [Установка и настройка](#установка-и-настройка)
4. [Запуск служб](#запуск-служб)
5. [Обработка видео](#обработка-видео)
6. [HLS/DASH стриминг](#hlsdash-стриминг)
7. [Система приоритетов](#система-приоритетов)
8. [Система алертов](#система-алертов)
9. [Management команды](#management-команды)
10. [Админ-панель](#админ-панель)
11. [API и интеграция](#api-и-интеграция)
12. [Мониторинг](#мониторинг)
13. [Troubleshooting](#troubleshooting)
14. [Production развертывание](#production-развертывание)

---

## Быстрый старт

### Минимальный запуск

```bash
# 1. Запуск Django
python manage.py runserver

# 2. Запуск Celery (новый терминал)
celery -A config worker -B -l info

# 3. Создание алертов
python manage.py create_default_alerts
```

**Готово!** Сайт доступен на http://127.0.0.1:8000

---

## Архитектура системы

### Компоненты

- **Django 5.2.8** - веб-фреймворк
- **Celery 5.3.4** - асинхронная обработка
- **Redis** - брокер сообщений и кэш
- **FFmpeg** - обработка видео
- **HLS/DASH** - адаптивный стриминг
- **HTMX 1.9.10** - динамический UI

### Модули

1. **apps/core** - базовая функциональность
2. **apps/videos** - обработка видео
3. **apps/users** - пользователи
4. **apps/comments** - комментарии
5. **apps/models** - модели/перформеры
6. **apps/ads** - реклама
7. **apps/localization** - переводы
---

#
# Установка и настройка

### Требования

- Python 3.11+
- FFmpeg
- Redis (для продакшена)
- PostgreSQL (для продакшена)

### Установка зависимостей

```bash
# Создание виртуального окружения
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Установка зависимостей
pip install -r requirements/development.txt
```

### Настройка базы данных

```bash
# Применение миграций
python manage.py migrate

# Создание суперпользователя
python manage.py createsuperuser
```

### Настройка переменных окружения

Создайте файл `.env`:
```bash
DJANGO_SETTINGS_MODULE=config.settings.development
SECRET_KEY=your-secret-key-here
DEBUG=True
CELERY_BROKER_URL=memory://
CELERY_RESULT_BACKEND=cache+memory://
```

---

## Запуск служб

### Development режим

**Терминал 1 - Django сервер:**
```bash
python manage.py runserver
# Доступен на: http://127.0.0.1:8000
```

**Терминал 2 - Celery worker:**
```bash
celery -A config worker -l info
```

**Терминал 3 - Celery beat (периодические задачи):**
```bash
celery -A config beat -l info
```

**Или все в одном (Celery):**
```bash
celery -A config worker -B -l info
```

### Production режим

**1. Установка Redis:**
```bash
# Windows (Chocolatey)
choco install redis-64

# Ubuntu/Debian
sudo apt install redis-server

# Запуск
redis-server
```

**2. Настройка production:**
```bash
# .env файл
DJANGO_SETTINGS_MODULE=config.settings.production
DEBUG=False
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

**3. Запуск с Gunicorn:**
```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```---


## Обработка видео

### Модульная архитектура

Система разделена на независимые сервисы:

- **FFmpegWrapper** - выполнение FFmpeg команд
- **MetadataExtractor** - извлечение метаданных
- **ThumbnailGenerator** - генерация превью
- **VideoEncoder** - кодирование видео
- **EncodingService** - координация процесса

### Профили кодирования

Создание через админку `/admin/videos/videoencodingprofile/`:

```python
# Рекомендуемые профили
360p Mobile: 640x360, 500 kbps
720p HD: 1280x720, 2500 kbps
1080p Full HD: 1920x1080, 5000 kbps
```

### Процесс обработки

1. **Загрузка** - пользователь загружает видео
2. **Валидация** - проверка формата и размера
3. **Анализ** - извлечение метаданных
4. **Кодирование** - параллельное создание профилей
5. **Публикация** - видео становится доступным

### Мониторинг обработки

```bash
# Просмотр активных задач
celery -A config inspect active

# Просмотр очереди
celery -A config inspect scheduled

# Статистика worker'ов
celery -A config inspect stats
```

---

## HLS/DASH стриминг

### Генерация стримов

**Для всех видео:**
```bash
python manage.py generate_streams
```

**Для конкретного видео:**
```bash
python manage.py generate_streams --video-id 123
```

**Только HLS:**
```bash
python manage.py generate_streams --stream-type hls
```

**Только DASH:**
```bash
python manage.py generate_streams --stream-type dash
```

**С ограничением:**
```bash
python manage.py generate_streams --limit 10
```

**Принудительная регенерация:**
```bash
python manage.py generate_streams --force
```

### Структура файлов

```
media/streams/
├── hls/{video_id}/
│   ├── 360p/playlist.m3u8
│   ├── 720p/playlist.m3u8
│   └── master.m3u8
└── dash/{video_id}/
    ├── 360p/manifest.mpd
    ├── 720p/manifest.mpd
    └── master.mpd
```

### Адаптивный плеер

Плеер автоматически:
- Выбирает лучший протокол (HLS → DASH → MP4)
- Переключает качество на основе скорости
- Предоставляет ручное управление качеством
- Fallback на стандартный MP4---

##
 Система приоритетов

### Уровни приоритетов

| Приоритет | Пользователи | Время ожидания |
|-----------|--------------|----------------|
| 9-10 | Premium | < 5 минут |
| 7-8 | Premium | 5-15 минут |
| 5 | Обычные | 15-30 минут |
| 3 | Новые | 30-60 минут |

### Управление приоритетами

**Установка premium статуса:**
```bash
python manage.py set_user_priority username --premium --priority 8
```

**Снятие premium:**
```bash
python manage.py set_user_priority username --no-premium
```

**Проверка приоритета:**
```bash
python manage.py set_user_priority username
```

**Установка приоритета без premium:**
```bash
python manage.py set_user_priority username --priority 6
```

### Динамический расчет

Система автоматически корректирует приоритет:
- Короткие видео (< 5 мин): +1
- Длинные видео (> 30 мин): -1
- Активные пользователи (> 50 видео): +1

---

## Система алертов

### Создание правил

```bash
python manage.py create_default_alerts
```

### Типы алертов

1. **Queue Size** - размер очереди (50/100 задач)
2. **Error Rate** - процент ошибок (20%)
3. **FFmpeg Unavailable** - недоступность FFmpeg
4. **Disk Space** - место на диске (85%/95%)
5. **Processing Time** - время обработки (30 мин)

### Настройка уведомлений

**Email настройка в settings.py:**
```python
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

**Webhook (Slack/Discord):**
1. Создать incoming webhook
2. Добавить URL в AlertRule через админку
3. Алерты будут отправляться автоматически

### Управление алертами

**Админ-панель:**
- Правила: `/admin/videos/alertrule/`
- Алерты: `/admin/videos/alert/`
- Метрики: `/admin/videos/systemmetric/`

**Программный доступ:**
```python
from apps.videos.services.alert_service import AlertService

service = AlertService()
health = service.get_system_health()
alerts = service.get_active_alerts()
```---


## Management команды

### Видео обработка

```bash
# Обработка ожидающих видео
python manage.py process_pending_videos

# Очистка старых черновиков
python manage.py cleanup_old_videos
```

### Пользователи

```bash
# Установка приоритета
python manage.py set_user_priority username --premium --priority 8

# Создание суперпользователя
python manage.py createsuperuser
```

### Стриминг

```bash
# Генерация всех стримов
python manage.py generate_streams

# Конкретное видео
python manage.py generate_streams --video-id 123

# Только HLS или DASH
python manage.py generate_streams --stream-type hls
python manage.py generate_streams --stream-type dash

# С ограничениями
python manage.py generate_streams --limit 10 --force
```

### Алерты

```bash
# Создание дефолтных правил
python manage.py create_default_alerts
```

### База данных

```bash
# Создание миграций
python manage.py makemigrations

# Применение миграций
python manage.py migrate

# Проверка миграций
python manage.py showmigrations

# Откат миграции
python manage.py migrate app_name 0001
```

### Статика и переводы

```bash
# Сбор статических файлов
python manage.py collectstatic --noinput

# Извлечение строк для перевода
python manage.py makemessages -l ru
python manage.py makemessages -l en

# Компиляция переводов
python manage.py compilemessages
```

### Разработка

```bash
# Запуск shell
python manage.py shell

# Проверка проекта
python manage.py check

# Проверка для продакшена
python manage.py check --deploy

# Создание приложения
python manage.py startapp app_name
```

---

## Админ-панель

### Основные разделы

**Видео управление:**
- `/admin/videos/video/` - управление видео
- `/admin/videos/videoencodingprofile/` - профили кодирования
- `/admin/videos/videostream/` - HLS/DASH стримы
- `/admin/videos/processingmetric/` - метрики обработки

**Система алертов:**
- `/admin/videos/alertrule/` - правила алертов
- `/admin/videos/alert/` - активные алерты
- `/admin/videos/systemmetric/` - системные метрики

**Пользователи:**
- `/admin/users/user/` - управление пользователями
- `/admin/auth/group/` - группы пользователей

**Контент:**
- `/admin/core/category/` - категории
- `/admin/core/tag/` - теги
- `/admin/models/model/` - модели/перформеры
- `/admin/comments/comment/` - комментарии

### Полезные функции

**Массовые операции:**
- Публикация видео
- Удаление видео
- Подтверждение алертов
- Изменение статуса пользователей

**Фильтры:**
- По статусу обработки
- По дате создания
- По пользователю
- По категории-
--

## API и интеграция

### HTMX endpoints

**Видео:**
- `POST /videos/htmx/{slug}/like/` - лайк видео
- `POST /videos/htmx/{slug}/favorite/` - добавить в избранное
- `POST /videos/htmx/{slug}/watch-later/` - добавить в "посмотреть позже"
- `GET /videos/htmx/{slug}/recommendations/` - рекомендации

**Рейтинги:**
- `POST /videos/htmx/{slug}/rating/` - оценка видео
- `GET /videos/htmx/{slug}/rating/widget/` - виджет рейтинга

**Прогресс обработки:**
- `GET /videos/api/progress/{video_id}/` - прогресс обработки
- `POST /videos/api/retry/{video_id}/` - повторная обработка

### Программный API

**Сервисы:**
```python
# Обработка видео
from apps.videos.services_encoding import VideoProcessingService
success = VideoProcessingService.process_video(video_id)

# Алерты
from apps.videos.services.alert_service import AlertService
service = AlertService()
health = service.get_system_health()

# Приоритеты
from apps.videos.services.priority_manager import PriorityManager
priority = PriorityManager.get_user_priority(user)
```

**Модели:**
```python
# Видео
from apps.videos.models import Video, VideoStream
video = Video.objects.published().with_related().first()

# Стримы
streams = video.streams.filter(is_ready=True)
has_hls = streams.filter(stream_type='hls').exists()

# Алерты
from apps.videos.models_alerts import Alert, AlertRule
active_alerts = Alert.objects.filter(status='active')
```

---

## Мониторинг

### Системные метрики

**Через админку:**
- `/admin/videos/systemmetric/` - все метрики
- `/admin/videos/processingmetric/` - метрики обработки
- `/admin/videos/alert/` - активные алерты

**Через код:**
```python
from apps.videos.services.alert_service import AlertService

service = AlertService()
health = service.get_system_health()
print(f"Queue: {health['queue_size']}")
print(f"Errors: {health['error_rate']}%")
print(f"Disk: {health['disk_usage_percent']}%")
```

### Celery мониторинг

```bash
# Активные задачи
celery -A config inspect active

# Запланированные задачи
celery -A config inspect scheduled

# Статистика worker'ов
celery -A config inspect stats

# Зарегистрированные задачи
celery -A config inspect registered
```

### Логирование

**Development:**
Логи выводятся в консоль.

**Production:**
Настройте логирование в `settings/production.py`:
```python
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': '/var/log/tubecms/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    },
}
```

### Мониторинг производительности

**Middleware включен:**
- `PerformanceMiddleware` - время запросов
- `DatabaseOptimizationMiddleware` - SQL запросы
- `CacheControlMiddleware` - кэширование

**Просмотр в логах:**
```
[PERFORMANCE] GET /videos/ took 0.234s
[DB] Query count: 12, time: 0.045s
```-
--

## Troubleshooting

### Частые проблемы

**1. FFmpeg не найден**
```bash
# Проверка
ffmpeg -version

# Установка Windows
choco install ffmpeg

# Установка Ubuntu
sudo apt install ffmpeg
```

**2. Celery не запускается**
```bash
# Проверка Redis
redis-cli ping

# Проверка настроек
echo $CELERY_BROKER_URL

# Перезапуск
celery -A config worker --purge
```

**3. Видео не обрабатывается**
```bash
# Проверка очереди
celery -A config inspect active

# Проверка логов
celery -A config worker -l debug

# Ручная обработка
python manage.py shell
>>> from apps.videos.services_encoding import VideoProcessingService
>>> VideoProcessingService.process_video(video_id)
```

**4. Стримы не генерируются**
```bash
# Проверка профилей
python manage.py shell
>>> from apps.videos.models_encoding import VideoEncodingProfile
>>> VideoEncodingProfile.objects.filter(is_active=True)

# Проверка файла
>>> video.temp_video_file.path
>>> import os; os.path.exists(video.temp_video_file.path)
```

**5. Алерты не работают**
```bash
# Проверка правил
python manage.py shell
>>> from apps.videos.models_alerts import AlertRule
>>> AlertRule.objects.filter(is_active=True)

# Ручная проверка
>>> from apps.videos.services.alert_service import AlertService
>>> AlertService().check_all_rules()
```

### Диагностические команды

```bash
# Проверка Django
python manage.py check
python manage.py check --deploy

# Проверка миграций
python manage.py showmigrations

# Проверка статики
python manage.py findstatic css/base.css

# Проверка переводов
python manage.py makemessages --dry-run

# Тест email
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Test', 'from@test.com', ['to@test.com'])
```

### Очистка системы

```bash
# Очистка кэша
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()

# Очистка Celery
celery -A config purge

# Очистка логов
rm -f logs/*.log  # Linux
del logs\*.log    # Windows

# Очистка миграций (осторожно!)
python manage.py migrate app_name zero
```

---

## Production развертывание

### Подготовка сервера

**1. Установка зависимостей:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv
sudo apt install postgresql postgresql-contrib
sudo apt install redis-server
sudo apt install ffmpeg
sudo apt install nginx
```

**2. Создание пользователя:**
```bash
sudo adduser tubecms
sudo usermod -aG sudo tubecms
```

### Настройка базы данных

```bash
# PostgreSQL
sudo -u postgres psql
CREATE DATABASE tubecms;
CREATE USER tubecms WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE tubecms TO tubecms;
\q
```

### Настройка приложения

**1. Клонирование и установка:**
```bash
cd /home/tubecms
git clone <repository>
cd TubeCMSv3
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/production.txt
```

**2. Переменные окружения (.env):**
```bash
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=very-long-random-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgres://tubecms:password@localhost/tubecms
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

**3. Миграции и статика:**
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py create_default_alerts
```##
# Настройка служб

**1. Gunicorn (systemd service):**
```bash
# /etc/systemd/system/tubecms.service
[Unit]
Description=TubeCMS Gunicorn daemon
After=network.target

[Service]
User=tubecms
Group=tubecms
WorkingDirectory=/home/tubecms/TubeCMSv3
ExecStart=/home/tubecms/TubeCMSv3/venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**2. Celery Worker (systemd service):**
```bash
# /etc/systemd/system/tubecms-celery.service
[Unit]
Description=TubeCMS Celery Worker
After=network.target

[Service]
User=tubecms
Group=tubecms
WorkingDirectory=/home/tubecms/TubeCMSv3
ExecStart=/home/tubecms/TubeCMSv3/venv/bin/celery -A config worker -l info
Restart=always

[Install]
WantedBy=multi-user.target
```

**3. Celery Beat (systemd service):**
```bash
# /etc/systemd/system/tubecms-celerybeat.service
[Unit]
Description=TubeCMS Celery Beat
After=network.target

[Service]
User=tubecms
Group=tubecms
WorkingDirectory=/home/tubecms/TubeCMSv3
ExecStart=/home/tubecms/TubeCMSv3/venv/bin/celery -A config beat -l info
Restart=always

[Install]
WantedBy=multi-user.target
```

**4. Nginx конфигурация:**
```nginx
# /etc/nginx/sites-available/tubecms
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    location /static/ {
        alias /home/tubecms/TubeCMSv3/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias /home/tubecms/TubeCMSv3/media/;
        expires 1y;
        add_header Cache-Control "public";
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**5. Запуск служб:**
```bash
sudo systemctl enable tubecms tubecms-celery tubecms-celerybeat
sudo systemctl start tubecms tubecms-celery tubecms-celerybeat
sudo systemctl enable nginx
sudo systemctl start nginx
```

### Мониторинг production

```bash
# Статус служб
sudo systemctl status tubecms
sudo systemctl status tubecms-celery
sudo systemctl status tubecms-celerybeat

# Логи
sudo journalctl -u tubecms -f
sudo journalctl -u tubecms-celery -f

# Перезапуск
sudo systemctl restart tubecms
sudo systemctl restart tubecms-celery
```

---

## Резервное копирование

### База данных

```bash
# Создание бэкапа
pg_dump -U tubecms -h localhost tubecms > backup_$(date +%Y%m%d).sql

# Восстановление
psql -U tubecms -h localhost tubecms < backup_20251126.sql
```

### Медиа файлы

```bash
# Бэкап медиа
tar -czf media_backup_$(date +%Y%m%d).tar.gz media/

# Восстановление
tar -xzf media_backup_20251126.tar.gz
```

### Автоматический бэкап (cron)

```bash
# crontab -e
0 2 * * * /home/tubecms/backup_script.sh
```

---

## Безопасность

### Настройки production

В `config/settings/production.py` уже настроено:
- `SECURE_SSL_REDIRECT = True`
- `SECURE_HSTS_SECONDS = 31536000`
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`

### Дополнительные меры

**1. Firewall:**
```bash
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

**2. SSL сертификат (Let's Encrypt):**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

**3. Регулярные обновления:**
```bash
sudo apt update && sudo apt upgrade
pip install --upgrade -r requirements/production.txt
```

---

## Заключение

TubeCMS v3 версии 2.0.0 включает:

✅ **8 основных функций:**
1. Модульная архитектура
2. Система приоритетов
3. Параллельное кодирование
4. HLS/DASH стриминг
5. Автоматическая очистка
6. Проверка диска
7. Метрики обработки
8. Система алертов

✅ **Production-ready:**
- Все проверки пройдены
- Документация полная
- Код без ошибок
- Готов к развертыванию

**Поддержка:** Все функции задокументированы и протестированы.

---

*Дата создания: 26 ноября 2025*  
*Версия: 2.0.0*  
*Статус: Production Ready*