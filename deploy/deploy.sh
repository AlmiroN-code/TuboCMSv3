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
sudo -u $PROJECT_USER ./venv/bin
log "Redis is running and responding"

# Create project directory
log "Creating project directory: $PROJECT_DIR"
mkdir -p $PROJECT_DIR
chown $PROJECT_USER:$PROJECT_USER $PROJECT_DIR

# Clone repository from GitHub
log "Cloning TubeCMS repository..."
if [ ! -d "$PROJECT_DIR/.git" ]; then
    if [ -d "$PROJECT_DIR" ]; then
        rm -rf $PROJECT_DIR
    fi
    
    git clone https://github.com/AlmiroN-code/TuboCMSv3.git $PROJECT_DIR
    
    if [ $? -eq 0 ]; then
        log "Repository cloned successfully"
    else
        error "Failed to clone repository. Please check your internet connection and try again."
    fi
    
    chown -R $PROJECT_USER:$PROJECT_USER $PROJECT_DIR
else
    log "Repository already exists, pulling latest changes..."
    cd $PROJECT_DIR
    sudo -u $PROJECT_USER git pull origin main || warning "Failed to pull latest changes"
fi

# Create Python virtual environment
log "Creating Python virtual environment..."
sudo -u $PROJECT_USER python3 -m venv $PROJECT_DIR/venv

# Create production environment file
log "Creating production environment configuration..."
cat > $PROJECT_DIR/.env << EOF
# Django Settings
SECRET_KEY=$(openssl rand -base64 32)
DEBUG=False
ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN,localhost,127.0.0.1

# Database (SQLite3)
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# Redis
REDIS_URL=redis://localhost:6379/1

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Email (Configure with your SMTP settings)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@$DOMAIN

# Media and Static
MEDIA_ROOT=$PROJECT_DIR/media/
STATIC_ROOT=$PROJECT_DIR/staticfiles/

# Security
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_BROWSER_XSS_FILTER=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Logging
LOG_LEVEL=INFO
LOG_FILE=$PROJECT_DIR/logs/django.log
EOF

chown $PROJECT_USER:$PROJECT_USER $PROJECT_DIR/.env
chmod 600 $PROJECT_DIR/.env

# Install Python dependencies
log "Installing Python dependencies..."
sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/pip install --upgrade pip wheel setuptools

# Install essential packages first
sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/pip install gunicorn transliterate python-decouple

if [ -f "$PROJECT_DIR/requirements/production.txt" ]; then
    sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/pip install -r $PROJECT_DIR/requirements/production.txt
elif [ -f "$PROJECT_DIR/requirements/base.txt" ]; then
    sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/pip install -r $PROJECT_DIR/requirements/base.txt
else
    sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/pip install Django==5.2.8 celery redis django-extensions whitenoise Pillow
fi

# Create all necessary directories
log "Creating project directories..."
mkdir -p $PROJECT_DIR/{logs,staticfiles}
mkdir -p $PROJECT_DIR/media/{videos,videos/tmp,posters,previews,avatars,models,ads,settings,streams}
mkdir -p $PROJECT_DIR/media/streams/{hls,dash}
mkdir -p /var/log/django
mkdir -p /var/run/celery

# Set ownership
chown -R $PROJECT_USER:www-data $PROJECT_DIR
chown -R $PROJECT_USER:www-data /var/log/django
chown -R $PROJECT_USER:www-data /var/run/celery

# Set permissions
chmod -R 755 $PROJECT_DIR
chmod -R 775 $PROJECT_DIR/media
chmod -R 775 $PROJECT_DIR/staticfiles
chmod -R 775 $PROJECT_DIR/logs
chmod -R 775 /var/log/django
chmod -R 775 /var/run/celery

# Run Django setup
log "Running Django migrations and setup..."
cd $PROJECT_DIR

# Test Django settings
log "Testing Django configuration..."
if ! sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/python manage.py check --settings=config.settings.production; then
    error "Django configuration check failed"
fi

# Run migrations
sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/python manage.py migrate --settings=config.settings.production || error "Django migrations failed"

# Set proper permissions for SQLite database file
if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
    chown $PROJECT_USER:www-data $PROJECT_DIR/db.sqlite3
    chmod 664 $PROJECT_DIR/db.sqlite3
    log "SQLite database permissions set"
fi

# Collect static files
log "Collecting static files..."
sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/python manage.py collectstatic --noinput --settings=config.settings.production || error "Static files collection failed"

# Create initial encoding profiles if they don't exist
log "Creating initial encoding profiles..."
sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/python manage.py shell --settings=config.settings.production << 'PYTHON_EOF'
from apps.videos.models_encoding import VideoEncodingProfile, MetadataExtractionSettings

# Create encoding profiles
profiles = [
    {"name": "360p", "resolution": "360p", "width": 640, "height": 360, "bitrate": 800, "order": 1},
    {"name": "480p", "resolution": "480p", "width": 854, "height": 480, "bitrate": 1200, "order": 2},
    {"name": "720p", "resolution": "720p", "width": 1280, "height": 720, "bitrate": 2500, "order": 3},
    {"name": "1080p", "resolution": "1080p", "width": 1920, "height": 1080, "bitrate": 5000, "order": 4},
]

for p in profiles:
    VideoEncodingProfile.objects.get_or_create(
        name=p["name"],
        defaults={
            "resolution": p["resolution"],
            "width": p["width"],
            "height": p["height"],
            "bitrate": p["bitrate"],
            "is_active": True,
            "order": p["order"],
        }
    )
print("Encoding profiles created/verified")

# Create metadata extraction settings
MetadataExtractionSettings.objects.get_or_create(
    is_active=True,
    defaults={
        "poster_width": 640,
        "poster_height": 360,
        "poster_format": "JPEG",
        "poster_quality": 85,
        "preview_width": 640,
        "preview_height": 360,
        "preview_duration": 12,
        "preview_segment_duration": 2,
        "preview_format": "MP4",
        "preview_quality": 85,
    }
)
print("Metadata extraction settings created/verified")
PYTHON_EOF

# Create alert rules
log "Creating alert rules..."
sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/python manage.py shell --settings=config.settings.production << 'PYTHON_EOF'
from apps.videos.models_alerts import AlertRule

rules = [
    {
        "name": "High Queue Size",
        "alert_type": "queue_size",
        "threshold_value": 50,
        "severity": "warning",
        "cooldown_minutes": 15,
    },
    {
        "name": "High Error Rate",
        "alert_type": "error_rate",
        "threshold_value": 10,
        "severity": "critical",
        "cooldown_minutes": 30,
    },
    {
        "name": "FFmpeg Unavailable",
        "alert_type": "ffmpeg_unavailable",
        "threshold_value": 0,
        "severity": "critical",
        "cooldown_minutes": 5,
    },
    {
        "name": "Low Disk Space",
        "alert_type": "disk_space",
        "threshold_value": 90,
        "severity": "critical",
        "cooldown_minutes": 60,
    },
]

for r in rules:
    AlertRule.objects.get_or_create(
        name=r["name"],
        defaults={
            "alert_type": r["alert_type"],
            "threshold_value": r["threshold_value"],
            "severity": r["severity"],
            "cooldown_minutes": r["cooldown_minutes"],
            "is_active": True,
        }
    )
print("Alert rules created/verified")
PYTHON_EOF

# Verify FFmpeg installation
log "Verifying FFmpeg installation..."
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version | head -n1)
    log "FFmpeg installed: $FFMPEG_VERSION"
else
    error "FFmpeg is not installed. Video processing will not work."
fi

# Create Gunicorn systemd service
log "Creating Gunicorn systemd service..."
cat > /etc/systemd/system/rextube.service << EOF
[Unit]
Description=RexTube Gunicorn daemon
Requires=rextube.socket
After=network.target redis.service

[Service]
Type=notify
User=$PROJECT_USER
Group=www-data
RuntimeDirectory=gunicorn
WorkingDirectory=$PROJECT_DIR
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
ExecStart=$PROJECT_DIR/venv/bin/gunicorn \\
    --access-logfile $PROJECT_DIR/logs/gunicorn-access.log \\
    --error-logfile $PROJECT_DIR/logs/gunicorn-error.log \\
    --workers 3 \\
    --timeout 120 \\
    --bind unix:$PROJECT_DIR/rextube.sock \\
    config.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=on-failure
RestartSec=5
KillMode=mixed
TimeoutStopSec=5

[Install]
WantedBy=multi-user.target
EOF

# Create Gunicorn socket
cat > /etc/systemd/system/rextube.socket << EOF
[Unit]
Description=RexTube Gunicorn socket

[Socket]
ListenStream=$PROJECT_DIR/rextube.sock
SocketUser=$PROJECT_USER
SocketGroup=www-data
SocketMode=0660

[Install]
WantedBy=sockets.target
EOF

# Create Celery worker systemd service
log "Creating Celery worker systemd service..."
cat > /etc/systemd/system/rextube-celery.service << EOF
[Unit]
Description=RexTube Celery Worker
After=network.target redis.service
Requires=redis.service

[Service]
Type=simple
User=$PROJECT_USER
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
Environment=CELERY_BROKER_URL=redis://localhost:6379/0
Environment=CELERY_RESULT_BACKEND=redis://localhost:6379/1
ExecStart=$PROJECT_DIR/venv/bin/celery -A config worker \\
    --loglevel=info \\
    --concurrency=2 \\
    --queues=celery,video_processing \\
    --logfile=$PROJECT_DIR/logs/celery-worker.log \\
    --pidfile=/var/run/celery/worker.pid
ExecStop=/bin/kill -TERM \$MAINPID
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
RuntimeDirectory=celery
RuntimeDirectoryMode=0755

[Install]
WantedBy=multi-user.target
EOF

# Create Celery beat systemd service
log "Creating Celery beat systemd service..."
cat > /etc/systemd/system/rextube-celery-beat.service << EOF
[Unit]
Description=RexTube Celery Beat Scheduler
After=network.target redis.service rextube-celery.service
Requires=redis.service

[Service]
Type=simple
User=$PROJECT_USER
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
Environment=CELERY_BROKER_URL=redis://localhost:6379/0
Environment=CELERY_RESULT_BACKEND=redis://localhost:6379/1
ExecStart=$PROJECT_DIR/venv/bin/celery -A config beat \\
    --loglevel=info \\
    --logfile=$PROJECT_DIR/logs/celery-beat.log \\
    --pidfile=/var/run/celery/beat.pid \\
    --scheduler=django_celery_beat.schedulers:DatabaseScheduler
ExecStop=/bin/kill -TERM \$MAINPID
Restart=always
RestartSec=10
RuntimeDirectory=celery
RuntimeDirectoryMode=0755

[Install]
WantedBy=multi-user.target
EOF

# Create tmpfiles.d config for /var/run/celery persistence
cat > /etc/tmpfiles.d/celery.conf << EOF
d /var/run/celery 0755 $PROJECT_USER www-data -
EOF

# Apply tmpfiles config
systemd-tmpfiles --create

# Configure Nginx
log "Configuring Nginx..."
cat > /etc/nginx/sites-available/$DOMAIN << EOF
# Upstream for Gunicorn
upstream rextube_app {
    server unix:$PROJECT_DIR/rextube.sock fail_timeout=0;
}

server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    # Security headers
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;
    
    # File upload size (for video uploads)
    client_max_body_size 500M;
    client_body_timeout 600s;
    
    # Static files with caching
    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
    
    # Media files
    location /media/ {
        alias $PROJECT_DIR/media/;
        expires 1M;
        add_header Cache-Control "public";
        
        # Enable range requests for video streaming
        add_header Accept-Ranges bytes;
    }
    
    # HLS streaming
    location /media/streams/hls/ {
        alias $PROJECT_DIR/media/streams/hls/;
        add_header Cache-Control "no-cache";
        add_header Access-Control-Allow-Origin *;
        
        # MIME types for HLS
        types {
            application/vnd.apple.mpegurl m3u8;
            video/mp2t ts;
        }
    }
    
    # DASH streaming
    location /media/streams/dash/ {
        alias $PROJECT_DIR/media/streams/dash/;
        add_header Cache-Control "no-cache";
        add_header Access-Control-Allow-Origin *;
        
        # MIME types for DASH
        types {
            application/dash+xml mpd;
            video/mp4 mp4 m4s;
        }
    }
    
    # Main application
    location / {
        proxy_pass http://rextube_app;
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        
        # Timeouts for long uploads
        proxy_connect_timeout 300s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json application/vnd.apple.mpegurl;
}
EOF

# Enable Nginx site
ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
nginx -t || error "Nginx configuration test failed"

# Configure firewall
log "Configuring firewall..."
ufw allow 'Nginx Full'
ufw allow OpenSSH
ufw --force enable

# Reload systemd and start services
log "Starting services..."
systemctl daemon-reload

# Enable all services
systemctl enable redis-server
systemctl enable nginx
systemctl enable rextube.socket
systemctl enable rextube
systemctl enable rextube-celery
systemctl enable rextube-celery-beat

# Start services in order
systemctl restart redis-server
sleep 2

systemctl restart nginx
sleep 1

# Start Gunicorn via socket
systemctl start rextube.socket
systemctl start rextube
sleep 2

# Start Celery services
log "Starting Celery worker..."
if systemctl start rextube-celery; then
    log "Celery worker started successfully"
else
    warning "Celery worker failed to start. Check logs: journalctl -u rextube-celery -n 50"
fi

sleep 2

log "Starting Celery beat..."
if systemctl start rextube-celery-beat; then
    log "Celery beat started successfully"
else
    warning "Celery beat failed to start. Check logs: journalctl -u rextube-celery-beat -n 50"
fi

# Check service status
log "Checking service status..."
echo ""
echo "=== Service Status ==="
systemctl --no-pager status redis-server | head -5
echo ""
systemctl --no-pager status nginx | head -5
echo ""
systemctl --no-pager status rextube | head -5
echo ""
systemctl --no-pager status rextube-celery | head -5
echo ""
systemctl --no-pager status rextube-celery-beat | head -5
echo ""

# Test socket file
if [ -S "$PROJECT_DIR/rextube.sock" ]; then
    log "Socket file created successfully"
else
    warning "Socket file not found. Checking Gunicorn status..."
    journalctl -u rextube -n 20 --no-pager
fi

# Setup SSL certificate
log "Setting up SSL certificate..."
if command -v certbot &> /dev/null; then
    info "Running Certbot to obtain SSL certificate..."
    certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN --redirect || warning "Certbot failed. You may need to run it manually."
else
    warning "Certbot not found. SSL certificate not configured."
fi

# Setup log rotation
log "Setting up log rotation..."
cat > /etc/logrotate.d/rextube << EOF
$PROJECT_DIR/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 644 $PROJECT_USER www-data
    sharedscripts
    postrotate
        systemctl reload rextube > /dev/null 2>&1 || true
        systemctl reload rextube-celery > /dev/null 2>&1 || true
    endscript
}
EOF

# Create maintenance scripts
log "Creating maintenance scripts..."

# Update script
cat > /usr/local/bin/rextube-update.sh << 'SCRIPT_EOF'
#!/bin/bash
PROJECT_DIR="/var/www/rextube.online"
PROJECT_USER="rextube"

echo "Updating TubeCMS..."
cd $PROJECT_DIR

# Pull latest changes
sudo -u $PROJECT_USER git pull origin main

# Update dependencies
sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/pip install -r requirements/production.txt

# Run migrations
sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/python manage.py migrate --settings=config.settings.production

# Set proper permissions for SQLite database
if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
    chown $PROJECT_USER:www-data $PROJECT_DIR/db.sqlite3
    chmod 664 $PROJECT_DIR/db.sqlite3
fi

# Collect static files
sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/python manage.py collectstatic --noinput --settings=config.settings.production

# Restart services
systemctl restart rextube
systemctl restart rextube-celery
systemctl restart rextube-celery-beat

echo "Update completed!"
SCRIPT_EOF
chmod +x /usr/local/bin/rextube-update.sh

# Status script
cat > /usr/local/bin/rextube-status.sh << 'SCRIPT_EOF'
#!/bin/bash
echo "=== TubeCMS Service Status ==="
echo ""
echo "Redis:"
systemctl is-active redis-server && redis-cli ping
echo ""
echo "Nginx:"
systemctl is-active nginx
echo ""
echo "Gunicorn (rextube):"
systemctl is-active rextube
echo ""
echo "Celery Worker:"
systemctl is-active rextube-celery
echo ""
echo "Celery Beat:"
systemctl is-active rextube-celery-beat
echo ""
echo "=== Celery Queue Status ==="
cd /var/www/rextube.online
sudo -u rextube ./venv/bin/celery -A config inspect active --timeout=5 2>/dev/null || echo "Could not inspect Celery"
echo ""
echo "=== Disk Usage ==="
df -h /var/www/rextube.online
echo ""
echo "=== Recent Errors ==="
tail -5 /var/www/rextube.online/logs/django.log 2>/dev/null || echo "No log file"
SCRIPT_EOF
chmod +x /usr/local/bin/rextube-status.sh

# Restart script
cat > /usr/local/bin/rextube-restart.sh << 'SCRIPT_EOF'
#!/bin/bash
echo "Restarting TubeCMS services..."
systemctl restart redis-server
sleep 2
systemctl restart rextube
systemctl restart rextube-celery
systemctl restart rextube-celery-beat
systemctl restart nginx
echo "All services restarted!"
/usr/local/bin/rextube-status.sh
SCRIPT_EOF
chmod +x /usr/local/bin/rextube-restart.sh

# Display completion message
log "Deployment completed successfully!"
info ""
info "=== DEPLOYMENT SUMMARY ==="
info "Domain: $DOMAIN"
info "Project directory: $PROJECT_DIR"
info "Project user: $PROJECT_USER"
info "Database: SQLite3 ($PROJECT_DIR/db.sqlite3)"
info ""
info "=== SERVICES ==="
info "✓ Nginx - Web server"
info "✓ Gunicorn - WSGI server"
info "✓ Redis - Cache & message broker"
info "✓ Celery Worker - Video processing queue"
info "✓ Celery Beat - Scheduled tasks"
info ""
info "=== FEATURES ENABLED ==="
info "✓ Automatic video encoding (360p, 480p, 720p, 1080p)"
info "✓ HLS streaming support"
info "✓ DASH streaming support"
info "✓ Poster & preview generation"
info "✓ Alert system (queue size, error rate, disk space)"
info "✓ Periodic cleanup tasks"
info ""
info "=== NEXT STEPS ==="
info "1. Create Django superuser:"
info "   sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/python $PROJECT_DIR/manage.py createsuperuser --settings=config.settings.production"
info ""
info "2. Configure email settings in $PROJECT_DIR/.env"
info ""
info "3. (Optional) Configure alert email recipients in admin panel"
info ""
info "=== USEFUL COMMANDS ==="
info "Check status:    /usr/local/bin/rextube-status.sh"
info "Restart all:     /usr/local/bin/rextube-restart.sh"
info "Update project:  /usr/local/bin/rextube-update.sh"
info "View logs:       journalctl -u rextube -f"
info "Celery logs:     journalctl -u rextube-celery -f"
info ""
info "=== TROUBLESHOOTING ==="
info "If video processing doesn't work:"
info "1. Check Celery: systemctl status rextube-celery"
info "2. Check Redis: redis-cli ping"
info "3. Check FFmpeg: ffmpeg -version"
info "4. Check logs: tail -f $PROJECT_DIR/logs/celery-worker.log"
info ""
info "Your TubeCMS installation should now be accessible at: https://$DOMAIN"
