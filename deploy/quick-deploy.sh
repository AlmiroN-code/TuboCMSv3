#!/bin/bash

# TubeCMS Quick Deployment Script
# One-command deployment for Ubuntu 24.04
# Domain: rextube.online
# Usage: curl -sSL https://raw.githubusercontent.com/AlmiroN-code/TuboCMSv3/main/deploy/quick-deploy.sh | sudo bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[TubeCMS] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root (use sudo)"
fi

log "🚀 Starting TubeCMS Quick Deployment for rextube.online"
echo ""

# Check system requirements
info "Checking system requirements..."

# Check Ubuntu version
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [[ "$ID" != "ubuntu" ]]; then
        warning "This script is designed for Ubuntu. Your OS: $ID"
    fi
    info "OS: $PRETTY_NAME"
fi

# Check available disk space
AVAILABLE_SPACE=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$AVAILABLE_SPACE" -lt 10 ]; then
    error "Insufficient disk space. At least 10GB required. Available: ${AVAILABLE_SPACE}GB"
fi
info "Available disk space: ${AVAILABLE_SPACE}GB"

# Check RAM
TOTAL_RAM=$(free -m | awk 'NR==2 {print $2}')
if [ "$TOTAL_RAM" -lt 1024 ]; then
    warning "Low RAM detected: ${TOTAL_RAM}MB. Recommended: 2GB+"
fi
info "Total RAM: ${TOTAL_RAM}MB"

echo ""

# Update system and install git
log "📦 Installing prerequisites..."
apt update >/dev/null 2>&1
apt install -y git curl wget >/dev/null 2>&1

# Download and run main deployment script
log "📥 Downloading TubeCMS deployment script..."
TEMP_DIR=$(mktemp -d)
cd $TEMP_DIR

# Download the main deployment script
wget -q https://raw.githubusercontent.com/AlmiroN-code/TuboCMSv3/main/deploy/deploy.sh -O deploy.sh

if [ ! -f "deploy.sh" ]; then
    error "Failed to download deployment script"
fi

# Make it executable
chmod +x deploy.sh

echo ""
log "🔧 Starting full deployment process..."
info "This will take 10-15 minutes to complete..."
echo ""
info "The script will automatically:"
info "  ✓ Clone TubeCMS from GitHub"
info "  ✓ Install Python, Redis, Nginx, FFmpeg"
info "  ✓ Configure SQLite database"
info "  ✓ Setup Celery workers for video processing"
info "  ✓ Configure HLS/DASH streaming"
info "  ✓ Setup SSL certificate"
info "  ✓ Enable alert system and metrics"
info "  ✓ Start all services"
echo ""

# Run the main deployment script
bash deploy.sh

# Cleanup
cd /
rm -rf $TEMP_DIR

echo ""
log "✅ TubeCMS Quick Deployment completed!"
echo ""
info "🌐 Your site should be available at: https://rextube.online"
info "🔧 Admin panel: https://rextube.online/admin/"
echo ""
info "📋 IMPORTANT - Next steps:"
echo ""
info "1. Create admin user:"
info "   sudo -u rextube /var/www/rextube.online/venv/bin/python /var/www/rextube.online/manage.py createsuperuser --settings=config.settings.production"
echo ""
info "2. Configure email settings (optional):"
info "   nano /var/www/rextube.online/.env"
echo ""
info "3. Check all services are running:"
info "   /usr/local/bin/rextube-status.sh"
echo ""
info "📊 Useful commands:"
info "   Status:   /usr/local/bin/rextube-status.sh"
info "   Restart:  /usr/local/bin/rextube-restart.sh"
info "   Update:   /usr/local/bin/rextube-update.sh"
info "   Logs:     journalctl -u rextube -f"
echo ""
info "🎬 Video Processing:"
info "   - Videos are automatically processed after upload"
info "   - Encoding profiles: 360p, 480p, 720p, 1080p"
info "   - HLS and DASH streaming enabled"
info "   - Check Celery: journalctl -u rextube-celery -f"
echo ""
warning "⚠️  If you encounter issues:"
info "   1. Check service status: systemctl status rextube rextube-celery"
info "   2. Check logs: tail -f /var/www/rextube.online/logs/*.log"
info "   3. Verify Redis: redis-cli ping"
info "   4. Verify FFmpeg: ffmpeg -version"
