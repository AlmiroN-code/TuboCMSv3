# RexTube Deployment Guide

Руководство по развертыванию RexTube на Ubuntu 24.04 для домена rextube.online.

**GitHub репозиторий**: https://github.com/AlmiroN-code/TuboCMSv3.git

> 🎥 **RexTube** - современная платформа для хостинга видео на Django 5.x с HTMX, Celery и полной системой обработки видео.

## 🚀 Автоматическое развертывание

### ⚡ Экспресс-развертывание (1 команда)

Для максимально быстрого развертывания выполните одну команду:

```bash
curl -sSL https://raw.githubusercontent.com/AlmiroN-code/TuboCMSv3/main/docs/quick-deploy.sh | sudo bash
```

Эта команда автоматически скачает и запустит полный процесс развертывания.

### 📋 Полное развертывание

### Предварительные требования

1. **Сервер Ubuntu 24.04** с root доступом
2. **Домен rextube.online** с настроенными DNS записями, указывающими на IP сервера
3. **SSH доступ** к серверу

### Шаг 1: Подготовка сервера

```bash
# Подключитесь к серверу
ssh root@your-server-ip

# Убедитесь, что git установлен
apt update && apt install -y git
```

**Примечание**: Скрипт развертывания автоматически клонирует проект из GitHub репозитория `https://github.com/AlmiroN-code/TuboCMSv3.git`

### Шаг 2: Запуск скрипта развертывания

```bash
# Скачайте и запустите скрипт развертывания
wget -O deploy.sh https://raw.githubusercontent.com/AlmiroN-code/TuboCMSv3/main/docs/deploy.sh
chmod +x deploy.sh
sudo bash deploy.sh

# Или клонируйте весь репозиторий и запустите скрипт:
git clone https://github.com/AlmiroN-code/TuboCMSv3.git
cd TuboCMSv3
sudo bash docs/deploy.sh
```

Скрипт автоматически:
- 📥 Клонирует проект из GitHub репозитория
- 🔄 Обновит систему
- 📦 Установит все необходимые зависимости (Python, PostgreSQL, Redis, Nginx, FFmpeg)
- 👤 Создаст пользователя и базу данных
- 🐍 Настроит виртуальное окружение Python
- ⚙️ Создаст файл .env с production настройками
- 🔧 Настроит systemd сервисы для Django и Celery
- 🌐 Настроит Nginx с оптимизацией
- 🔒 Получит SSL сертификат от Let's Encrypt
- 📝 Настроит ротацию логов

## ⚙️ Пост-развертывание

### Шаг 3: Финальная настройка

```bash
# 1. Обновите пароль базы данных
sudo -u postgres psql
ALTER USER tubecms WITH PASSWORD 'your_strong_password';
\q

# 2. Обновите .env файл
nano /var/www/tubecms/.env
# Измените DB_PASSWORD на новый пароль
# Настройте EMAIL_HOST_USER и EMAIL_HOST_PASSWORD

# 3. Установите зависимости Python
cd /var/www/tubecms
sudo -u tubecms ./venv/bin/pip install -r requirements/production.txt
sudo -u tubecms ./venv/bin/pip install transliterate

# 4. Выполните миграции
sudo -u tubecms ./venv/bin/python manage.py migrate --settings=config.settings.production

# 5. Соберите статические файлы
sudo -u tubecms ./venv/bin/python manage.py collectstatic --noinput --settings=config.settings.production

# 6. Создайте суперпользователя
sudo -u tubecms ./venv/bin/python manage.py createsuperuser --settings=config.settings.production

# 7. Перезапустите сервисы
systemctl restart tubecms tubecms-celery tubecms-celery-beat
```

## 🔧 Управление системой

### Полезные команды

```bash
# Просмотр статуса сервисов
systemctl status tubecms
systemctl status tubecms-celery
systemctl status tubecms-celery-beat

# Просмотр логов
journalctl -u tubecms -f
journalctl -u tubecms-celery -f
tail -f /var/www/tubecms/logs/django.log

# Перезапуск сервисов
systemctl restart tubecms
systemctl restart tubecms-celery
systemctl restart nginx

# Обновление проекта
/usr/local/bin/tubecms-update.sh

# Проверка конфигурации Nginx
nginx -t
nginx -s reload
```

### Мониторинг

```bash
# Проверка работы сайта
curl -I https://rextube.online

# Проверка SSL сертификата
openssl s_client -connect rextube.online:443 -servername rextube.online

# Проверка Redis
redis-cli ping

# Проверка PostgreSQL
sudo -u postgres psql -c "SELECT version();"
```

## 🛡️ Безопасность

### Обязательные настройки безопасности

1. **Смените пароли по умолчанию**:
   ```bash
   # PostgreSQL
   sudo -u postgres psql
   ALTER USER tubecms WITH PASSWORD 'strong_password_here';
   ```

2. **Настройте файрвол**:
   ```bash
   ufw status
   ufw allow 'Nginx Full'
   ufw allow OpenSSH
   ufw enable
   ```

3. **Обновите SECRET_KEY в .env**

4. **Настройте резервное копирование**:
   ```bash
   # Создайте скрипт резервного копирования
   cat > /usr/local/bin/backup-tubecms.sh << 'EOF'
   #!/bin/bash
   BACKUP_DIR="/var/backups/tubecms"
   DATE=$(date +%Y%m%d_%H%M%S)
   
   mkdir -p $BACKUP_DIR
   
   # Бэкап базы данных
   sudo -u postgres pg_dump tubecms > $BACKUP_DIR/db_$DATE.sql
   
   # Бэкап медиа файлов
   tar -czf $BACKUP_DIR/media_$DATE.tar.gz -C /var/www/tubecms media/
   
   # Удаление старых бэкапов (старше 7 дней)
   find $BACKUP_DIR -type f -mtime +7 -delete
   EOF
   
   chmod +x /usr/local/bin/backup-tubecms.sh
   
   # Добавьте в crontab (ежедневно в 2:00)
   crontab -e
   # Добавьте строку: 0 2 * * * /usr/local/bin/backup-tubecms.sh
   ```

## 🔧 Настройка производительности

### Оптимизация PostgreSQL

```bash
# Отредактируйте postgresql.conf
nano /etc/postgresql/16/main/postgresql.conf

# Рекомендуемые настройки:
shared_buffers = 128MB
effective_cache_size = 512MB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
```

### Оптимизация Redis

```bash
# Отредактируйте redis.conf
nano /etc/redis/redis.conf

# Рекомендуемые настройки:
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

## 🚨 Устранение неполадок

### Частые проблемы

1. **Сервис не запускается**:
   ```bash
   journalctl -u tubecms --no-pager
   # Проверьте права доступа к файлам
   chown -R tubecms:www-data /var/www/tubecms
   ```

2. **Ошибки базы данных**:
   ```bash
   # Проверьте подключение к БД
   sudo -u tubecms psql -h localhost -U tubecms -d tubecms
   ```

3. **Проблемы с SSL**:
   ```bash
   # Обновление сертификата
   certbot renew --dry-run
   ```

4. **502 Bad Gateway**:
   ```bash
   # Проверьте, что Gunicorn запущен
   systemctl status tubecms
   # Проверьте права на sock файл
   ls -la /var/www/tubecms/tubecms.sock
   ```

## 📊 Мониторинг и логи

### Структура логов

- **Django**: `/var/www/tubecms/logs/django.log`
- **Nginx**: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`
- **Systemd services**: `journalctl -u service-name`

### Настройка мониторинга (опционально)

Для продвинутого мониторинга можно установить:
- **Grafana + Prometheus** для метрик
- **ELK Stack** для логов
- **Sentry** для отслеживания ошибок

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи сервисов
2. Убедитесь, что все сервисы запущены
3. Проверьте настройки файрвола
4. Проверьте DNS записи домена

---

## 💡 Краткое резюме

**RexTube** - полнофункциональная платформа для хостинга видео с:

- 🌍 **Современный стек**: Django 5.x + HTMX + Bootstrap 5
- 🎥 **Обработка видео**: FFmpeg + Celery для асинхронной конвертации
- 📊 **Масштабируемость**: PostgreSQL + Redis + Nginx
- 🔒 **Безопасность**: SSL, CSRF защита, валидация
- 🎨 **Пользовательский интерфейс**: адаптивные темы, HTMX интеракции

### 🔗 Полезные ссылки

- **GitHub**: https://github.com/AlmiroN-code/TuboCMSv3.git
- **Техническая документация**: `/docs/VIDEO_PROCESSING.md`
- **Экспресс-развертывание**: `curl -sSL https://raw.githubusercontent.com/AlmiroN-code/TuboCMSv3/main/docs/quick-deploy.sh | sudo bash`

**🎉 Поздравляем! RexTube успешно развернут на https://rextube.online** 🎆
