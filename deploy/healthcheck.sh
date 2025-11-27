#!/bin/bash

# TubeCMS Health Check Script
# Verifies all services are running correctly

set -e

PROJECT_DIR="/var/www/rextube.online"
PROJECT_USER="rextube"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() {
    echo -e "${GREEN}✓ $1${NC}"
}

fail() {
    echo -e "${RED}✗ $1${NC}"
}

warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

echo "=== TubeCMS Health Check ==="
echo ""

# Check Redis
echo "Checking Redis..."
if redis-cli ping > /dev/null 2>&1; then
    pass "Redis is running"
else
    fail "Redis is not responding"
fi

# Check Nginx
echo "Checking Nginx..."
if systemctl is-active --quiet nginx; then
    pass "Nginx is running"
else
    fail "Nginx is not running"
fi

# Check Gunicorn
echo "Checking Gunicorn..."
if systemctl is-active --quiet rextube; then
    pass "Gunicorn is running"
else
    fail "Gunicorn is not running"
fi

# Check socket file
echo "Checking socket..."
if [ -S "$PROJECT_DIR/rextube.sock" ]; then
    pass "Socket file exists"
else
    fail "Socket file not found"
fi

# Check Celery Worker
echo "Checking Celery Worker..."
if systemctl is-active --quiet rextube-celery; then
    pass "Celery Worker is running"
else
    fail "Celery Worker is not running"
fi

# Check Celery Beat
echo "Checking Celery Beat..."
if systemctl is-active --quiet rextube-celery-beat; then
    pass "Celery Beat is running"
else
    fail "Celery Beat is not running"
fi

# Check FFmpeg
echo "Checking FFmpeg..."
if command -v ffmpeg &> /dev/null; then
    pass "FFmpeg is installed"
else
    fail "FFmpeg is not installed"
fi

# Check database
echo "Checking Database..."
if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
    pass "SQLite database exists"
    # Check if writable
    if [ -w "$PROJECT_DIR/db.sqlite3" ]; then
        pass "Database is writable"
    else
        fail "Database is not writable"
    fi
else
    fail "Database file not found"
fi

# Check media directories
echo "Checking Media directories..."
MEDIA_DIRS=("videos" "posters" "previews" "avatars" "streams/hls" "streams/dash")
for dir in "${MEDIA_DIRS[@]}"; do
    if [ -d "$PROJECT_DIR/media/$dir" ]; then
        pass "Media/$dir exists"
    else
        warn "Media/$dir missing"
    fi
done

# Check static files
echo "Checking Static files..."
if [ -d "$PROJECT_DIR/staticfiles" ] && [ "$(ls -A $PROJECT_DIR/staticfiles 2>/dev/null)" ]; then
    pass "Static files collected"
else
    warn "Static files may not be collected"
fi

# Check encoding profiles
echo "Checking Encoding profiles..."
PROFILES=$(sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/python $PROJECT_DIR/manage.py shell --settings=config.settings.production -c "from apps.videos.models_encoding import VideoEncodingProfile; print(VideoEncodingProfile.objects.filter(is_active=True).count())" 2>/dev/null)
if [ "$PROFILES" -gt 0 ]; then
    pass "Found $PROFILES active encoding profiles"
else
    warn "No encoding profiles found"
fi

# Check Celery queue
echo "Checking Celery queue..."
CELERY_STATUS=$(sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/celery -A config inspect ping --timeout=5 2>/dev/null | grep -c "pong" || echo "0")
if [ "$CELERY_STATUS" -gt 0 ]; then
    pass "Celery workers responding"
else
    warn "Celery workers not responding (may be starting)"
fi

# Check disk space
echo "Checking Disk space..."
DISK_USAGE=$(df -h $PROJECT_DIR | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    pass "Disk usage: ${DISK_USAGE}%"
elif [ "$DISK_USAGE" -lt 90 ]; then
    warn "Disk usage: ${DISK_USAGE}% (getting high)"
else
    fail "Disk usage: ${DISK_USAGE}% (critical)"
fi

# Test Django
echo "Checking Django..."
if sudo -u $PROJECT_USER $PROJECT_DIR/venv/bin/python $PROJECT_DIR/manage.py check --settings=config.settings.production > /dev/null 2>&1; then
    pass "Django check passed"
else
    fail "Django check failed"
fi

echo ""
echo "=== Health Check Complete ==="
