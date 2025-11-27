#!/bin/bash

# TubeCMS Deployment Script for Ubuntu 24.04
# Domain: rextube.online | Database: SQLite3
# Usage: sudo bash deploy.sh

set -e

DOMAIN="rextube.online"
PROJECT_USER="rextube"
PROJECT_DIR="/var/www/rextube.online"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"; }
error() { echo -e "${RED}[ERROR] $1${NC}"; exit 1; }
warn() { echo -e "${YELLOW}[WARN] $1${NC}"; }
info() { echo -e "${BLUE}[INFO] $1${NC}"; }

[[ $EUID -ne 0 ]] && error "Run as root: sudo bash deploy.sh"

log "=== TubeCMS Deployment for $DOMAIN ==="

# 1. System packages
log "Installing system packages..."
apt update && apt install -y python3 python3-venv python3-dev python3-pip \
    redis-server nginx git curl wget build-essential libjpeg-dev libpng-dev \
    libwebp-dev libfreetype6-dev libffi-dev libssl-dev pkg-config ffmpeg \
    certbot python3-certbot-nginx htop ufw

# 2. Create user
if ! id "$PROJECT_USER" &>/dev/null; then
    useradd -m -s /bin/bash $PROJECT_USER
    usermod -aG www-data $PROJECT_USER
    log "User $PROJECT_USER created"
fi

# 3. Redis
systemctl enable --now redis-server
redis-cli ping > /dev/null || error "Redis not responding"
log "Redis OK"

# 4. Clone/update repo
log "Setting up project..."
if [ -d "$PROJECT_DIR/.git" ]; then
    cd $PROJECT_DIR && sudo -u $PROJECT_USER git pull origin main || true
else
    rm -rf $PROJECT_DIR
    git clone https://github.com/AlmiroN-code/TuboCMSv3.git $PROJECT_DIR
fi
chown -R $PROJECT_USER:www-data $PROJECT_DIR

# 5. Virtual environment
log "Setting up Python environment..."
sudo -u $PROJECT_USER python3 -m venv $PROJECT_DIR/venv
sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/pip install -q --upgrade pip wheel

# 6. Install dependencies
if [ -f "$PROJECT_DIR/requirements/production.txt" ]; then
    sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/pip install -q -r $PROJECT_DIR/requirements/production.txt
else
    sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/pip install -q -r $PROJECT_DIR/requirements/base.txt
fi
sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/pip install -q gunicorn

# 7. Environment file
log "Creating .env..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cat > $PROJECT_DIR/.env << EOF
SECRET_KEY=$(openssl rand -base64 32)
DEBUG=False
ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN,localhost,127.0.0.1
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
REDIS_URL=redis://localhost:6379/1
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
MEDIA_ROOT=$PROJECT_DIR/media/
STATIC_ROOT=$PROJECT_DIR/staticfiles/
LOG_FILE=$PROJECT_DIR/logs/django.log
SECURE_SSL_REDIRECT=False
EOF
    chown $PROJECT_USER:$PROJECT_USER $PROJECT_DIR/.env
    chmod 600 $PROJECT_DIR/.env
fi

# 8. Directories
log "Creating directories..."
mkdir -p $PROJECT_DIR/{logs,staticfiles}
mkdir -p $PROJECT_DIR/media/{videos,videos/tmp,posters,previews,avatars,models,streams/hls,streams/dash}
chown -R $PROJECT_USER:www-data $PROJECT_DIR
chmod -R 775 $PROJECT_DIR/media $PROJECT_DIR/logs $PROJECT_DIR/staticfiles

# 9. Django setup
log "Running Django setup..."
cd $PROJECT_DIR
sudo -u $PROJECT_USER ./venv/bin/python manage.py migrate --settings=config.settings.production
sudo -u $PROJECT_USER ./venv/bin/python manage.py collectstatic --noinput --settings=config.settings.production

# Set DB permissions
[ -f "$PROJECT_DIR/db.sqlite3" ] && chown $PROJECT_USER:www-data $PROJECT_DIR/db.sqlite3 && chmod 664 $PROJECT_DIR/db.sqlite3

# 10. Setup encoding profiles and alert rules using management commands
log "Setting up encoding profiles..."
sudo -u $PROJECT_USER ./venv/bin/python manage.py setup_encoding --settings=config.settings.production || warn "setup_encoding failed"

log "Creating default alert rules..."
sudo -u $PROJECT_USER ./venv/bin/python manage.py create_default_alerts --settings=config.settings.production || warn "create_default_alerts failed"

# Create additional encoding profiles (480p)
log "Creating additional encoding profiles..."
sudo -u $PROJECT_USER ./venv/bin/python manage.py shell --settings=config.settings.production << 'PYEOF'
from apps.videos.models_encoding import VideoEncodingProfile
VideoEncodingProfile.objects.get_or_create(
    name="480p",
    defaults={"resolution": "480p", "width": 854, "height": 480, "bitrate": 1200, "order": 2, "is_active": True}
)
print("480p profile created/verified")
PYEOF

# 11. Remove old socket config if exists
systemctl stop rextube.socket 2>/dev/null || true
systemctl disable rextube.socket 2>/dev/null || true
rm -f /etc/systemd/system/rextube.socket

# 12. Systemd services
log "Creating systemd services..."

# Gunicorn (without socket - direct bind)
cat > /etc/systemd/system/rextube.service << EOF
[Unit]
Description=RexTube Gunicorn
After=network.target redis.service

[Service]
User=$PROJECT_USER
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --workers 3 --timeout 120 --bind unix:$PROJECT_DIR/rextube.sock config.wsgi:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Celery Worker
cat > /etc/systemd/system/rextube-celery.service << EOF
[Unit]
Description=RexTube Celery Worker
After=network.target redis.service
Requires=redis.service

[Service]
User=$PROJECT_USER
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
ExecStart=$PROJECT_DIR/venv/bin/celery -A config worker -l info -c 2 -Q celery,video_processing
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Celery Beat (with DatabaseScheduler for django_celery_beat)
cat > /etc/systemd/system/rextube-celery-beat.service << EOF
[Unit]
Description=RexTube Celery Beat
After=network.target redis.service
Requires=redis.service

[Service]
User=$PROJECT_USER
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
ExecStart=$PROJECT_DIR/venv/bin/celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 13. Nginx
log "Configuring Nginx..."
cat > /etc/nginx/sites-available/$DOMAIN << EOF
upstream rextube { server unix:$PROJECT_DIR/rextube.sock fail_timeout=0; }
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    client_max_body_size 500M;
    
    location /static/ { alias $PROJECT_DIR/staticfiles/; expires 1y; }
    location /media/ { alias $PROJECT_DIR/media/; expires 1M; add_header Accept-Ranges bytes; }
    location /media/streams/hls/ { alias $PROJECT_DIR/media/streams/hls/; types { application/vnd.apple.mpegurl m3u8; video/mp2t ts; } }
    location /media/streams/dash/ { alias $PROJECT_DIR/media/streams/dash/; types { application/dash+xml mpd; video/mp4 mp4 m4s; } }
    location / {
        proxy_pass http://rextube;
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 300s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }
}
EOF
ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t || error "Nginx config error"

# 14. Firewall
ufw allow 'Nginx Full' > /dev/null 2>&1 || true
ufw allow OpenSSH > /dev/null 2>&1 || true
ufw --force enable > /dev/null 2>&1 || true

# 15. Start everything
log "Starting all services..."
systemctl daemon-reload

# Stop all if running
systemctl stop rextube rextube-celery rextube-celery-beat 2>/dev/null || true

# Enable and start
systemctl enable --now redis-server
systemctl enable --now nginx
systemctl enable --now rextube
sleep 2
systemctl enable --now rextube-celery
sleep 1
systemctl enable --now rextube-celery-beat

# 16. Verify
log "Verifying services..."
sleep 3

check_service() {
    if systemctl is-active --quiet $1; then
        echo -e "  ${GREEN}✓ $1${NC}"
    else
        echo -e "  ${RED}✗ $1${NC}"
        journalctl -u $1 -n 5 --no-pager
    fi
}

echo ""
check_service redis-server
check_service nginx
check_service rextube
check_service rextube-celery
check_service rextube-celery-beat
echo ""

# Check socket
[ -S "$PROJECT_DIR/rextube.sock" ] && log "Socket OK" || warn "Socket not found"

# 17. SSL (optional)
log "Setting up SSL..."
certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN --redirect 2>/dev/null || warn "SSL setup failed - run manually: certbot --nginx -d $DOMAIN"

# 18. Helper scripts
cat > /usr/local/bin/rextube-restart << 'EOF'
#!/bin/bash
systemctl restart rextube rextube-celery rextube-celery-beat nginx
echo "Services restarted"
EOF
chmod +x /usr/local/bin/rextube-restart

cat > /usr/local/bin/rextube-status << 'EOF'
#!/bin/bash
for s in redis-server nginx rextube rextube-celery rextube-celery-beat; do
    printf "%-20s %s\n" "$s:" "$(systemctl is-active $s)"
done
EOF
chmod +x /usr/local/bin/rextube-status

cat > /usr/local/bin/rextube-logs << 'EOF'
#!/bin/bash
journalctl -u rextube -u rextube-celery -u rextube-celery-beat -f
EOF
chmod +x /usr/local/bin/rextube-logs

cat > /usr/local/bin/rextube-update << 'EOF'
#!/bin/bash
cd /var/www/rextube.online
sudo -u rextube git pull origin main
sudo -u rextube ./venv/bin/pip install -r requirements/production.txt
sudo -u rextube ./venv/bin/python manage.py migrate --settings=config.settings.production
sudo -u rextube ./venv/bin/python manage.py collectstatic --noinput --settings=config.settings.production
systemctl restart rextube rextube-celery rextube-celery-beat
echo "Update complete"
EOF
chmod +x /usr/local/bin/rextube-update

# Done
log "=== DEPLOYMENT COMPLETE ==="
echo ""
info "Site: https://$DOMAIN"
info "Admin: https://$DOMAIN/admin/"
echo ""
info "Create admin user:"
info "  sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/python $PROJECT_DIR/manage.py createsuperuser --settings=config.settings.production"
echo ""
info "Commands: rextube-status | rextube-restart | rextube-logs | rextube-update"
echo ""
info "Features:"
info "  ✓ Auto video encoding (360p, 480p, 720p, 1080p)"
info "  ✓ Poster & preview generation"
info "  ✓ HLS/DASH streaming"
info "  ✓ Alert system"
info "  ✓ Periodic tasks (cleanup, monitoring)"
echo ""

# Final status
rextube-status
