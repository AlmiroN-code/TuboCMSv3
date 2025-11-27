#!/bin/bash

# TubeCMS Deployment Script for Ubuntu 24.04
# Domain: rextube.online
# Usage: sudo bash deploy.sh

set -e  # Exit on any error

# Configuration
DOMAIN="rextube.online"
PROJECT_NAME="rextube"
PROJECT_USER="rextube"
PROJECT_DIR="/var/www/rextube.online"
PYTHON_VERSION="3.12"
REDIS_PORT="6379"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root (use sudo)"
fi

log "Starting TubeCMS deployment for $DOMAIN"

# Update system
log "Updating system packages..."
apt update && apt upgrade -y

# Install system dependencies
log "Installing system dependencies..."
apt install -y \
    python3 \
    python3-venv \
    python3-dev \
    python3-pip \
    redis-server \
    nginx \
    git \
    curl \
    wget \
    unzip \
    build-essential \
    libjpeg-dev \
    libpng-dev \
    libwebp-dev \
    libfreetype6-dev \
    libffi-dev \
    libssl-dev \
    pkg-config \
    ffmpeg \
    supervisor \
    certbot \
    python3-certbot-nginx \
    htop \
    ufw

# Create project user
log "Creating project user: $PROJECT_USER"
if ! id "$PROJECT_USER" &>/dev/null; then
    useradd -m -s /bin/bash $PROJECT_USER
    usermod -aG www-data $PROJECT_USER
fi

# Setup SQLite database
log "Setting up SQLite database..."
# SQLite database file will be created automatically by Django migrations
# Ensure proper permissions will be set after migrations

# Configure Redis
log "Configuring Redis..."
systemctl enable redis-server
systemctl start redis-server

# Create project directory
log "Creating project directory: $PROJECT_DIR"
mkdir -p $PROJECT_DIR
chown $PROJECT_USER:$PROJECT_USER $PROJECT_DIR

# Clone repository from GitHub
log "Cloning TubeCMS repository..."
if [ ! -d "$PROJECT_DIR/.git" ]; then
    # Remove existing directory if it exists but is not a git repo
    if [ -d "$PROJECT_DIR" ]; then
        rm -rf $PROJECT_DIR
    fi
    
    # Clone the repository
    git clone https://github.com/AlmiroN-code/TuboCMSv3.git $PROJECT_DIR
    
    if [ $? -eq 0 ]; then
        log "Repository cloned successfully"
    else
        error "Failed to clone repository. Please check your internet connection and try again."
    fi
    
    # Set ownership
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

# Database (SQLite)
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=$PROJECT_DIR/db.sqlite3

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Email (Configure with your SMTP settings)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

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
sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/pip install --upgrade pip

# Install essential packages first
sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/pip install gunicorn transliterate python-decouple

if [ -f "$PROJECT_DIR/requirements/production.txt" ]; then
    sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/pip install -r $PROJECT_DIR/requirements/production.txt
else
    # Install basic requirements if file not found
    sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/pip install Django==5.0.1 celery redis django-extensions whitenoise
fi

# Run Django setup
log "Running Django migrations and setup..."
cd $PROJECT_DIR

# Create logs directory and system log dirs
mkdir -p $PROJECT_DIR/logs
mkdir -p /var/log/django
chown -R $PROJECT_USER:$PROJECT_USER $PROJECT_DIR/logs
chown -R $PROJECT_USER:www-data /var/log/django
chmod -R 775 $PROJECT_DIR/logs
chmod -R 775 /var/log/django

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

# Create and set up directories before collecting static files
log "Setting up staticfiles and media directories..."
mkdir -p $PROJECT_DIR/{media,staticfiles}
mkdir -p $PROJECT_DIR/media/{videos,posters,previews,avatars,models}

# Ensure staticfiles and media directories have correct ownership and permissions
if [ ! -d "$PROJECT_DIR/staticfiles" ]; then
    mkdir -p $PROJECT_DIR/staticfiles
fi
if [ ! -d "$PROJECT_DIR/media" ]; then
    mkdir -p $PROJECT_DIR/media
fi

chown -R $PROJECT_USER:www-data $PROJECT_DIR/staticfiles
chown -R $PROJECT_USER:www-data $PROJECT_DIR/media
chmod -R 775 $PROJECT_DIR/staticfiles
chmod -R 775 $PROJECT_DIR/media

# Collect static files
log "Collecting static files..."
sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/python manage.py collectstatic --noinput --settings=config.settings.production || error "Static files collection failed"

# Create Gunicorn systemd service
log "Creating Gunicorn systemd service..."
cat > /etc/systemd/system/rextube.service << EOF
[Unit]
Description=RexTube Gunicorn daemon
After=network.target

[Service]
Type=notify
User=$PROJECT_USER
Group=www-data
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --access-logfile - --workers 3 --bind unix:$PROJECT_DIR/rextube.sock config.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=on-failure
RestartSec=5
KillMode=mixed
TimeoutStopSec=5
Environment=DJANGO_SETTINGS_MODULE=config.settings.production

[Install]
WantedBy=multi-user.target
EOF

# Create Celery worker systemd service
log "Creating Celery worker systemd service..."
cat > /etc/systemd/system/rextube-celery.service << EOF
[Unit]
Description=RexTube Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=$PROJECT_USER
Group=www-data
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/celery -A config worker -l info --pidfile=/var/run/celery/worker.pid --detach
ExecStop=$PROJECT_DIR/venv/bin/celery -A config worker --pidfile=/var/run/celery/worker.pid --loglevel=info
ExecReload=$PROJECT_DIR/venv/bin/celery -A config worker --pidfile=/var/run/celery/worker.pid --loglevel=info --restart
Restart=always
Environment=DJANGO_SETTINGS_MODULE=config.settings.production

[Install]
WantedBy=multi-user.target
EOF

# Create Celery beat systemd service
log "Creating Celery beat systemd service..."
cat > /etc/systemd/system/rextube-celery-beat.service << EOF
[Unit]
Description=RexTube Celery Beat
After=network.target redis.service

[Service]
Type=forking
User=$PROJECT_USER
Group=www-data
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/celery -A config beat -l info --pidfile=/var/run/celery/beat.pid --detach
ExecStop=/bin/kill -TERM \$MAINPID
Restart=always
Environment=DJANGO_SETTINGS_MODULE=config.settings.production

[Install]
WantedBy=multi-user.target
EOF

# Create directories for Celery PID files
mkdir -p /var/run/celery
chown $PROJECT_USER:www-data /var/run/celery

# Configure Nginx
log "Configuring Nginx..."
cat > /etc/nginx/sites-available/$DOMAIN << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy strict-origin-when-cross-origin;
    
    # File upload size
    client_max_body_size 100M;
    
    # Static files
    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias $PROJECT_DIR/media/;
        expires 1M;
        add_header Cache-Control "public";
    }
    
    # Main application
    location / {
        proxy_pass http://unix:$PROJECT_DIR/rextube.sock;
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        
        # Timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
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

# Create remaining directories and set permissions
log "Setting up remaining directories and permissions..."
mkdir -p $PROJECT_DIR/logs
# Create log directories for production settings
mkdir -p /var/log/django

# Set ownership first
chown -R $PROJECT_USER:www-data $PROJECT_DIR
chown -R $PROJECT_USER:www-data /var/log/django

# Set permissions
chmod -R 755 $PROJECT_DIR
chmod -R 775 $PROJECT_DIR/media
chmod -R 775 $PROJECT_DIR/staticfiles
chmod -R 775 $PROJECT_DIR/logs
chmod -R 775 /var/log/django

# Start and enable services
log "Starting services..."
systemctl daemon-reload
systemctl enable nginx
systemctl enable rextube
systemctl enable rextube-celery
systemctl enable rextube-celery-beat

systemctl restart nginx

# Start services with detailed error checking
log "Starting RexTube services..."
if systemctl start rextube; then
    log "RexTube service started successfully"
else
    error "RexTube service failed to start. Check logs with: journalctl -u rextube -n 50"
fi

if systemctl start rextube-celery; then
    log "Celery worker started successfully"
else
    warning "Celery worker failed to start. Check logs with: journalctl -u rextube-celery -n 50"
fi

if systemctl start rextube-celery-beat; then
    log "Celery beat started successfully"
else
    warning "Celery beat failed to start. Check logs with: journalctl -u rextube-celery-beat -n 50"
fi

# Check service status
log "Checking service status..."
systemctl --no-pager status rextube nginx

# Test socket file
if [ -S "$PROJECT_DIR/rextube.sock" ]; then
    log "Socket file created successfully"
    ls -la $PROJECT_DIR/rextube.sock
else
    warning "Socket file not found. This may cause 502 errors."
fi

# Setup SSL certificate
log "Setting up SSL certificate..."
if command -v certbot &> /dev/null; then
    info "Running Certbot to obtain SSL certificate..."
    certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN --redirect
else
    warning "Certbot not found. SSL certificate not configured."
fi

# Setup log rotation
log "Setting up log rotation..."
cat > /etc/logrotate.d/rextube << EOF
$PROJECT_DIR/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 $PROJECT_USER $PROJECT_USER
    postrotate
        systemctl reload rextube
    endscript
}
EOF

# Create maintenance script
log "Creating maintenance scripts..."
cat > /usr/local/bin/rextube-update.sh << 'EOF'
#!/bin/bash
PROJECT_DIR="/var/www/rextube.online"
PROJECT_USER="rextube"

echo "Updating TubeCMS..."
cd $PROJECT_DIR

# Pull latest changes
git pull origin main

# Update dependencies
sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/pip install -r requirements/production.txt

# Ensure directories exist and have correct permissions before running migrations and collecting static files
if [ ! -d "$PROJECT_DIR/staticfiles" ]; then
    mkdir -p $PROJECT_DIR/staticfiles
    chown $PROJECT_USER:www-data $PROJECT_DIR/staticfiles
    chmod 775 $PROJECT_DIR/staticfiles
fi
if [ ! -d "$PROJECT_DIR/media" ]; then
    mkdir -p $PROJECT_DIR/media
    chown $PROJECT_USER:www-data $PROJECT_DIR/media 
    chmod 775 $PROJECT_DIR/media
fi

# Run migrations and collect static files
sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/python manage.py migrate --settings=config.settings.production

# Set proper permissions for SQLite database file
if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
    chown $PROJECT_USER:www-data $PROJECT_DIR/db.sqlite3
    chmod 664 $PROJECT_DIR/db.sqlite3
fi

sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/python manage.py collectstatic --noinput --settings=config.settings.production

# Restart services
systemctl restart rextube
systemctl restart rextube-celery
systemctl restart rextube-celery-beat

echo "Update completed!"
EOF

chmod +x /usr/local/bin/rextube-update.sh

# Display completion message
log "Deployment completed successfully!"
info ""
info "=== DEPLOYMENT SUMMARY ==="
info "Domain: $DOMAIN"
info "Project directory: $PROJECT_DIR"
info "Project user: $PROJECT_USER"
info "Database: SQLite (db.sqlite3)"
info ""
info "=== NEXT STEPS ==="
info "1. Project files automatically cloned from GitHub"
info "2. Database configuration already set (SQLite)"
info "3. Configure email settings in $PROJECT_DIR/.env"
info "4. Create Django superuser: sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/python $PROJECT_DIR/manage.py createsuperuser --settings=config.settings.production"
info "5. Restart services: systemctl restart rextube rextube-celery rextube-celery-beat"
info ""
info "=== USEFUL COMMANDS ==="
info "Update project: /usr/local/bin/rextube-update.sh"
info "View logs: journalctl -u rextube -f"
info "Restart services: systemctl restart rextube"
info ""
info "=== SECURITY NOTES ==="
warning "1. SQLite database is stored in $PROJECT_DIR/db.sqlite3"
warning "2. Configure proper email settings"
warning "3. Review firewall settings"
warning "4. Setup regular backups"
info ""
info "Your TubeCMS installation should now be accessible at: https://$DOMAIN"
info ""
info "=== TROUBLESHOOTING 502 ERRORS ==="
info "If you get 502 Bad Gateway, run these commands:"
info "1. Check RexTube service: systemctl status rextube"
info "2. Check logs: journalctl -u rextube -f"
info "3. Check socket file: ls -la $PROJECT_DIR/rextube.sock"
info "4. Test Django directly: sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/python $PROJECT_DIR/manage.py runserver 127.0.0.1:8000 --settings=config.settings.production"
info "5. Check nginx error logs: tail -f /var/log/nginx/error.log"
