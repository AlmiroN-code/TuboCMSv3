#!/bin/bash

# TubeCMS Quick Deployment Script
# One-command deployment for Ubuntu 24.04
# Usage: curl -sSL https://raw.githubusercontent.com/AlmiroN-code/TuboCMSv3/main/docs/quick-deploy.sh | sudo bash

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

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root (use sudo)"
fi

log "🚀 Starting TubeCMS Quick Deployment for rextube.online"

# Update system and install git
log "📦 Installing git..."
apt update >/dev/null 2>&1
apt install -y git >/dev/null 2>&1

# Download and run main deployment script
log "📥 Downloading TubeCMS deployment script..."
TEMP_DIR=$(mktemp -d)
cd $TEMP_DIR

# Download the main deployment script
wget -q https://raw.githubusercontent.com/AlmiroN-code/TuboCMSv3/main/docs/deploy.sh -O deploy.sh

if [ ! -f "deploy.sh" ]; then
    error "Failed to download deployment script"
fi

# Make it executable
chmod +x deploy.sh

log "🔧 Starting full deployment process..."
info "This will take 10-15 minutes to complete..."
info "The script will automatically:"
info "  - Clone TubeCMS from GitHub"
info "  - Install all dependencies"
info "  - Configure database and services"
info "  - Setup SSL certificate"
info "  - Start all services"

# Run the main deployment script
bash deploy.sh

# Cleanup
cd /
rm -rf $TEMP_DIR

log "✅ TubeCMS Quick Deployment completed!"
info "🌐 Your site should be available at: https://rextube.online"
info "🔧 Admin panel: https://rextube.online/admin/"
info ""
info "📋 Next steps:"
info "1. Update database password: nano /var/www/tubecms/.env"
info "2. Configure email settings in .env"
info "3. Create admin user: sudo -u tubecms /var/www/tubecms/venv/bin/python /var/www/tubecms/manage.py createsuperuser --settings=config.settings.production"
info "4. Restart services: systemctl restart tubecms tubecms-celery tubecms-celery-beat"
info ""
info "🔍 Check status: systemctl status tubecms nginx"
info "📊 View logs: journalctl -u tubecms -f"
