# Все команды TubeCMS v3

## Django Management Commands

### Основные команды
```bash
# Запуск сервера
python manage.py runserver

# Миграции
python manage.py makemigrations
python manage.py migrate

# Создать суперпользователя
python manage.py createsuperuser

# Собрать статику
python manage.py collectstatic --noinput

# Оболочка Django
python manage.py shell
```

### Видео команды
```bash
# Обработать видео
python manage.py process_videos
python manage.py process_videos --priority=high
python manage.py process_videos --limit=10

# Очистить неудачные видео
python manage.py cleanup_failed_videos
python manage.py cleanup_failed_videos --days=7
python manage.py cleanup_failed_videos --dry-run

# Статистика видео
python manage.py video_stats
python manage.py video_stats --format=json
python manage.py video_stats --format=csv

# Проверить обработку
python manage.py check_processing_status

# Пересоздать миниатюры
python manage.py regenerate_thumbnails

# Проверить целостность файлов
python manage.py check_video_files

# Генерация HLS/DASH стримов
python manage.py generate_streams
python manage.py generate_streams --video-id 123
python manage.py generate_streams --stream-type hls
python manage.py generate_streams --stream-type dash

# Установить приоритет пользователя
python manage.py set_user_priority username --premium --priority 8
python manage.py set_user_priority username --no-premium
python manage.py set_user_priority username  # проверить приоритет
```

### Кэш команды
```bash
# Очистить весь кэш
python manage.py clear_cache

# Очистить по паттерну
python manage.py clear_cache --pattern=videos:*

# Статистика кэша
python manage.py cache_stats

# Прогреть кэш
python manage.py warmup_cache
```

### Пользователи
```bash
# Создать тестовых пользователей
python manage.py create_test_users
python manage.py create_test_users --count=50

# Статистика пользователей
python manage.py user_stats
python manage.py user_stats --active-only

# Очистить неактивных пользователей
python manage.py cleanup_inactive_users --days=365
```

### Алерты и мониторинг
```bash
# Создать алерты по умолчанию
python manage.py create_default_alerts

# Проверить алерты
python manage.py check_alerts

# Тест алертов
python manage.py test_alerts

# Проверить место на диске
python manage.py check_disk_space

# Проверить правила алертов (каждые 5 минут через Celery)
# Автоматически через: apps.videos.tasks.check_alert_rules
```

### Переводы
```bash
# Извлечь строки для перевода
python manage.py makemessages -l ru
python manage.py makemessages -l en
python manage.py makemessages --all  # все языки

# Скомпилировать переводы
python manage.py compilemessages

# Создать минимальные .mo файлы (без gettext)
python create_minimal_mo.py

# Компилировать переводы для конкретного языка
python compile_translations.py
```

### База данных
```bash
# Дамп базы
python manage.py dumpdata > backup.json
python manage.py dumpdata --indent=2 > backup.json

# Загрузить данные
python manage.py loaddata backup.json

# Сброс миграций
python manage.py migrate --fake-initial

# SQL команды
python manage.py dbshell
```

### Тестирование
```bash
# Запустить все тесты
pytest

# Тесты с покрытием
pytest --cov=apps

# Конкретный тест
pytest apps/videos/tests.py

# Тест конкретного метода
pytest apps/videos/tests.py::TestVideoModel::test_video_creation

# Тест с выводом
pytest -v -s

# Только неудачные тесты
pytest --lf
```

### Специальные команды системы
```bash
# Тестирование обработки видео напрямую
python test_video_direct.py

# Проверка синтаксиса всего проекта
python manage.py check

# Проверка миграций
python manage.py check --deploy

# Показать SQL миграций
python manage.py sqlmigrate app_name migration_number

# Откатить миграцию
python manage.py migrate app_name migration_number

# Показать план миграций
python manage.py showmigrations
```

---

## Celery Commands

### Запуск Celery
```bash
# Worker + Beat вместе
celery -A config worker -B -l info

# Только worker
celery -A config worker -l info

# Только beat (планировщик)
celery -A config beat -l info

# С автоперезагрузкой
celery -A config worker --reload -l info
```

### Мониторинг Celery
```bash
# Статус воркеров
celery -A config status

# Активные задачи
celery -A config active

# Зарегистрированные задачи
celery -A config inspect registered

# Статистика
celery -A config inspect stats

# Очистить очередь
celery -A config purge

# Показать очереди
celery -A config inspect active_queues

# Отменить задачу
celery -A config control revoke task_id

# Перезапустить воркеры
celery -A config control pool_restart

# Мониторинг в реальном времени
celery -A config events

# Flower (веб-интерфейс для мониторинга)
celery -A config flower
```

---

## Системные команды

### Процессы
```bash
# Найти процессы Django
ps aux | grep manage.py

# Найти процессы Celery
ps aux | grep celery

# Убить процесс
kill -9 PID

# Убить все процессы Celery
pkill -f celery
```

### Логи
```bash
# Логи Django (если используется systemd)
journalctl -u tubecms -f

# Логи Celery
journalctl -u celery-worker -f
journalctl -u celery-beat -f

# Логи в файлы
tail -f logs/django.log
tail -f logs/celery.log
```

### Диск и файлы
```bash
# Проверить место
df -h

# Размер папки media
du -sh media/

# Найти большие файлы
find media/ -size +100M -ls

# Очистить временные файлы
find /tmp -name "*.tmp" -delete
```

---

## Git команды

### Основные
```bash
# Статус
git status

# Добавить файлы
git add .
git add filename

# Коммит
git commit -m "Сообщение"

# Пуш
git push origin main

# Пулл
git pull origin main
```

### Ветки
```bash
# Создать ветку
git checkout -b feature-name

# Переключиться
git checkout main

# Список веток
git branch -a

# Удалить ветку
git branch -d feature-name
```

---

## Docker команды (если используется)

### Основные
```bash
# Сборка
docker-compose build

# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Логи
docker-compose logs -f

# Выполнить команду в контейнере
docker-compose exec web python manage.py migrate
```

---

## Nginx команды

### Управление
```bash
# Перезагрузить конфиг
sudo nginx -s reload

# Проверить конфиг
sudo nginx -t

# Перезапустить
sudo systemctl restart nginx

# Статус
sudo systemctl status nginx

# Логи
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

---

## Redis команды

### CLI
```bash
# Подключиться
redis-cli

# Проверить подключение
redis-cli ping

# Информация
redis-cli info

# Очистить базу
redis-cli flushdb

# Мониторинг
redis-cli monitor
```

### В Redis CLI
```redis
# Посмотреть ключи
KEYS *
KEYS videos:*

# Получить значение
GET key_name

# Удалить ключ
DEL key_name

# TTL ключа
TTL key_name

# Статистика памяти
INFO memory
```

---

## PostgreSQL команды (для продакшена)

### Подключение
```bash
# Подключиться к базе
psql -U username -d database_name

# Дамп базы
pg_dump -U username database_name > backup.sql

# Восстановить базу
psql -U username database_name < backup.sql
```

### В psql
```sql
-- Список таблиц
\dt

-- Описание таблицы
\d table_name

-- Размер базы
SELECT pg_size_pretty(pg_database_size('database_name'));

-- Активные соединения
SELECT * FROM pg_stat_activity;
```

---

## Полезные алиасы

Добавь в `.bashrc` или `.zshrc`:

```bash
# Django
alias dj="python manage.py"
alias djrun="python manage.py runserver"
alias djmig="python manage.py migrate"
alias djmake="python manage.py makemigrations"
alias djshell="python manage.py shell"

# Celery
alias celerywork="celery -A config worker -B -l info"
alias celerystatus="celery -A config status"

# Git
alias gs="git status"
alias ga="git add ."
alias gc="git commit -m"
alias gp="git push origin main"

# Системные
alias ll="ls -la"
alias ..="cd .."
alias grep="grep --color=auto"
```

---

## Быстрые команды для разработки

### Полный перезапуск
```bash
# Остановить все
pkill -f celery
pkill -f runserver

# Применить миграции
python manage.py migrate

# Запустить заново
python manage.py runserver &
celery -A config worker -B -l info &
```

### Сброс базы (разработка)
```bash
# Удалить базу
rm db.sqlite3

# Пересоздать миграции
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

# Создать заново
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### Очистка кэша и временных файлов
```bash
# Очистить кэш Django
python manage.py clear_cache

# Очистить Redis
redis-cli flushdb

# Очистить Python кэш
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

# Очистить логи
> logs/django.log
> logs/celery.log
```

---

## Команды для продакшена

### Развертывание
```bash
# Обновить код
git pull origin main

# Установить зависимости
pip install -r requirements/production.txt

# Применить миграции
python manage.py migrate

# Собрать статику
python manage.py collectstatic --noinput

# Перезапустить сервисы
sudo systemctl restart tubecms
sudo systemctl restart celery-worker
sudo systemctl restart celery-beat
sudo systemctl reload nginx
```

### Мониторинг
```bash
# Проверить статус сервисов
sudo systemctl status tubecms
sudo systemctl status celery-worker
sudo systemctl status celery-beat
sudo systemctl status nginx
sudo systemctl status redis

# Проверить логи
journalctl -u tubecms -f --lines=50
journalctl -u celery-worker -f --lines=50

# Проверить ресурсы
htop
df -h
free -h
```

### Бэкапы
```bash
# Бэкап базы данных (PostgreSQL)
pg_dump -U tubecms tubecms_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Бэкап базы данных (SQLite для разработки)
cp db.sqlite3 backup_db_$(date +%Y%m%d_%H%M%S).sqlite3

# Бэкап медиа файлов
tar -czf media_backup_$(date +%Y%m%d_%H%M%S).tar.gz media/

# Бэкап конфигов
tar -czf config_backup_$(date +%Y%m%d_%H%M%S).tar.gz /etc/nginx/ /etc/systemd/system/tubecms*

# Бэкап через Django
python manage.py dumpdata > full_backup_$(date +%Y%m%d_%H%M%S).json
python manage.py dumpdata --indent=2 > readable_backup_$(date +%Y%m%d_%H%M%S).json

# Восстановление из бэкапа
python manage.py loaddata backup_file.json
```

---

## Специальные команды из документации

### Обработка видео (из MODULAR_ARCHITECTURE.md)
```bash
# Использование модульной архитектуры
python manage.py shell
>>> from apps.videos.services_encoding import VideoProcessingService as EncodingService
>>> success = EncodingService.process_video(video_id, selected_profiles)
```

### Система приоритетов (из PRIORITY_QUEUE.md)
```bash
# Установка приоритетов пользователей
python manage.py set_user_priority username --premium --priority 8
python manage.py set_user_priority username --no-premium
python manage.py set_user_priority username  # проверить текущий приоритет

# Проверка очереди приоритетов через shell
python manage.py shell
>>> from apps.videos.services.priority_manager import PriorityManager
>>> priority = PriorityManager.get_user_priority(user)
>>> position = PriorityManager.estimate_queue_position(user)
```

### Система алертов (из ALERTS.md)
```bash
# Создание правил алертов
python manage.py create_default_alerts

# Проверка алертов вручную
python manage.py shell
>>> from apps.videos.services.alert_service import AlertService
>>> AlertService.check_all_rules()
>>> health = AlertService.get_system_health()
>>> alerts = AlertService.get_active_alerts()
```

### Метрики обработки (из PROCESSING_METRICS.md)
```bash
# Просмотр метрик через админку
# Перейти на /admin/videos/processingmetric/

# Анализ метрик через shell
python manage.py shell
>>> from apps.videos.models import ProcessingMetric
>>> metrics = ProcessingMetric.objects.filter(status='success')
>>> avg_time = metrics.aggregate(avg_time=models.Avg('processing_time'))
```

### HLS/DASH стриминг (из STREAMING.md)
```bash
# Генерация всех стримов
python manage.py generate_streams

# Генерация для конкретного видео
python manage.py generate_streams --video-id 123

# Только HLS стримы
python manage.py generate_streams --stream-type hls

# Только DASH стримы  
python manage.py generate_streams --stream-type dash

# Проверка готовности стримов
python manage.py shell
>>> from apps.videos.models import VideoStream
>>> streams = VideoStream.objects.filter(is_ready=True)
```

### Проверка диска (из DISK_SPACE_CHECK.md)
```bash
# Проверка места через management команду
python manage.py check_disk_space

# Проверка через сервис
python manage.py shell
>>> from apps.videos.services.ffmpeg_wrapper import FFmpegWrapper
>>> has_space, free_bytes, msg = FFmpegWrapper.check_disk_space("/media", 1024*1024*1024)
>>> print(f"Free space: {free_bytes / (1024**3):.1f}GB")
```

### Очистка ошибок (из ERROR_CLEANUP.md)
```bash
# Автоматическая очистка включена по умолчанию в EncodingService
# Ручная очистка временных файлов
find /tmp -name "*.tmp" -delete
find media/temp -name "*" -delete 2>/dev/null || true

# Очистка неудачных обработок
python manage.py cleanup_failed_videos --days=7 --dry-run
python manage.py cleanup_failed_videos --days=7
```

---

## Команды для отладки

### Проверка состояния системы
```bash
# Проверка всех компонентов
python manage.py check --deploy

# Проверка FFmpeg
ffmpeg -version
which ffmpeg

# Проверка Redis
redis-cli ping
redis-cli info

# Проверка места на диске
df -h
du -sh media/

# Проверка процессов
ps aux | grep python
ps aux | grep celery
ps aux | grep redis
```

### Логирование и отладка
```bash
# Включить отладочные логи Django
export DJANGO_LOG_LEVEL=DEBUG
python manage.py runserver

# Логи Celery с максимальной детализацией
celery -A config worker -l debug

# Мониторинг файлов в реальном времени
tail -f logs/django.log
tail -f logs/celery.log
tail -f /var/log/nginx/access.log

# Проверка использования памяти
free -h
top -p $(pgrep -f "python|celery")
```

### Тестирование производительности
```bash
# Нагрузочное тестирование (если установлен ab)
ab -n 100 -c 10 http://localhost:8000/

# Профилирование Django запросов
python manage.py shell
>>> from django.db import connection
>>> connection.queries  # после выполнения запросов

# Тест скорости обработки видео
time python test_video_direct.py
```

---

## Windows-специфичные команды

### PowerShell команды
```powershell
# Список процессов Python
Get-Process | Where-Object {$_.ProcessName -like "*python*"}

# Убить процесс по имени
Stop-Process -Name "python" -Force

# Проверка портов
netstat -an | findstr :8000
netstat -an | findstr :6379

# Размер папки
Get-ChildItem -Path "media" -Recurse | Measure-Object -Property Length -Sum

# Очистка временных файлов
Remove-Item -Path "temp\*" -Recurse -Force
```

### CMD команды
```cmd
# Найти процессы
tasklist | findstr python
tasklist | findstr celery

# Убить процесс
taskkill /f /im python.exe

# Проверка сервисов
sc query Redis
sc query nginx

# Копирование с заменой
xcopy /s /y media\* backup\media\
```

---

## Команды для CI/CD

### Автоматизация развертывания
```bash
#!/bin/bash
# deploy.sh

# Обновление кода
git pull origin main

# Виртуальное окружение
source venv/bin/activate

# Зависимости
pip install -r requirements/production.txt

# Миграции
python manage.py migrate --noinput

# Статика
python manage.py collectstatic --noinput

# Перезапуск сервисов
sudo systemctl restart tubecms
sudo systemctl restart celery-worker
sudo systemctl restart celery-beat
sudo systemctl reload nginx

# Проверка
sleep 5
curl -f http://localhost/ || echo "Deployment failed!"
```

### Проверка перед развертыванием
```bash
# Тесты
pytest --maxfail=1

# Линтинг (если установлен)
flake8 apps/
black --check apps/

# Проверка безопасности
python manage.py check --deploy

# Проверка миграций
python manage.py makemigrations --dry-run --check
```