#!/bin/bash
# =============================================================================
# Let's Encrypt SSL Certificate Setup for A2A SNS System
# =============================================================================
# Usage:
#   ./setup-letsencrypt.sh your-domain.com your-email@example.com
#
# Requirements:
#   - Domain must point to this server's IP
#   - Port 80 must be accessible from internet
#   - Run as root or with sudo
# =============================================================================

set -e

DOMAIN="${1:-}"
EMAIL="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SSL_DIR="$SCRIPT_DIR/ssl"
CERTBOT_DIR="/etc/letsencrypt/live/$DOMAIN"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_error() { echo -e "${RED}ERROR: $1${NC}" >&2; }
print_success() { echo -e "${GREEN}$1${NC}"; }
print_warning() { echo -e "${YELLOW}$1${NC}"; }

# =============================================================================
# Validation
# =============================================================================
if [ -z "$DOMAIN" ]; then
    print_error "Domain name required"
    echo "Usage: $0 <domain> <email>"
    echo "Example: $0 api.example.com admin@example.com"
    exit 1
fi

if [ -z "$EMAIL" ]; then
    print_error "Email address required for Let's Encrypt notifications"
    echo "Usage: $0 <domain> <email>"
    exit 1
fi

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root or with sudo"
    exit 1
fi

echo "=========================================="
echo "Let's Encrypt SSL Setup"
echo "=========================================="
echo "Domain: $DOMAIN"
echo "Email:  $EMAIL"
echo "=========================================="
echo ""

# =============================================================================
# Install Certbot
# =============================================================================
echo "Step 1: Installing Certbot..."

if command -v apt-get &> /dev/null; then
    # Debian/Ubuntu
    apt-get update
    apt-get install -y certbot
elif command -v yum &> /dev/null; then
    # Amazon Linux / CentOS
    yum install -y certbot
elif command -v dnf &> /dev/null; then
    # Fedora / Amazon Linux 2023
    dnf install -y certbot
else
    print_error "Package manager not supported. Install certbot manually."
    exit 1
fi

print_success "Certbot installed"

# =============================================================================
# Stop nginx temporarily (for standalone mode)
# =============================================================================
echo ""
echo "Step 2: Stopping nginx temporarily..."

if docker ps | grep -q nginx; then
    docker stop $(docker ps -q --filter "ancestor=nginx:alpine") 2>/dev/null || true
    print_success "Nginx container stopped"
fi

if systemctl is-active --quiet nginx 2>/dev/null; then
    systemctl stop nginx
    print_success "Nginx service stopped"
fi

# =============================================================================
# Obtain Certificate
# =============================================================================
echo ""
echo "Step 3: Obtaining SSL certificate from Let's Encrypt..."

certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    --domain "$DOMAIN" \
    --preferred-challenges http

if [ ! -d "$CERTBOT_DIR" ]; then
    print_error "Certificate not found at $CERTBOT_DIR"
    exit 1
fi

print_success "Certificate obtained!"

# =============================================================================
# Copy Certificates to nginx ssl directory
# =============================================================================
echo ""
echo "Step 4: Copying certificates to nginx directory..."

mkdir -p "$SSL_DIR"

# Copy with proper permissions
cp "$CERTBOT_DIR/fullchain.pem" "$SSL_DIR/cert.pem"
cp "$CERTBOT_DIR/privkey.pem" "$SSL_DIR/key.pem"

chmod 644 "$SSL_DIR/cert.pem"
chmod 600 "$SSL_DIR/key.pem"

print_success "Certificates copied to $SSL_DIR"

# =============================================================================
# Update nginx.conf with domain
# =============================================================================
echo ""
echo "Step 5: Updating nginx configuration..."

NGINX_CONF="$SCRIPT_DIR/nginx.conf"
if [ -f "$NGINX_CONF" ]; then
    # Replace server_name _; with actual domain
    sed -i "s/server_name _;/server_name $DOMAIN;/g" "$NGINX_CONF"
    print_success "nginx.conf updated with domain: $DOMAIN"
fi

# =============================================================================
# Setup Auto-Renewal
# =============================================================================
echo ""
echo "Step 6: Setting up auto-renewal..."

# Create renewal hook script
RENEWAL_HOOK="/etc/letsencrypt/renewal-hooks/deploy/a2a-ssl-reload.sh"
mkdir -p "$(dirname "$RENEWAL_HOOK")"

cat > "$RENEWAL_HOOK" << 'HOOK_EOF'
#!/bin/bash
# Copy renewed certificates to nginx directory
DOMAIN="__DOMAIN__"
SSL_DIR="__SSL_DIR__"
CERTBOT_DIR="/etc/letsencrypt/live/$DOMAIN"

if [ -d "$CERTBOT_DIR" ]; then
    cp "$CERTBOT_DIR/fullchain.pem" "$SSL_DIR/cert.pem"
    cp "$CERTBOT_DIR/privkey.pem" "$SSL_DIR/key.pem"
    chmod 644 "$SSL_DIR/cert.pem"
    chmod 600 "$SSL_DIR/key.pem"

    # Reload nginx
    docker exec $(docker ps -q --filter "ancestor=nginx:alpine") nginx -s reload 2>/dev/null || true
    systemctl reload nginx 2>/dev/null || true
fi
HOOK_EOF

# Replace placeholders
sed -i "s|__DOMAIN__|$DOMAIN|g" "$RENEWAL_HOOK"
sed -i "s|__SSL_DIR__|$SSL_DIR|g" "$RENEWAL_HOOK"
chmod +x "$RENEWAL_HOOK"

# Add cron job for renewal check
CRON_JOB="0 3 * * * certbot renew --quiet"
(crontab -l 2>/dev/null | grep -v "certbot renew"; echo "$CRON_JOB") | crontab -

print_success "Auto-renewal configured (daily check at 3 AM)"

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "=========================================="
print_success "Let's Encrypt SSL Setup Complete!"
echo "=========================================="
echo ""
echo "Certificate files:"
echo "  - $SSL_DIR/cert.pem"
echo "  - $SSL_DIR/key.pem"
echo ""
echo "Auto-renewal:"
echo "  - Cron job: Daily at 3 AM"
echo "  - Hook: $RENEWAL_HOOK"
echo ""
echo "Next steps:"
echo "  1. Start the system:"
echo "     cd $(dirname "$SCRIPT_DIR")"
echo "     docker-compose -f docker-compose.ec2.yml up -d"
echo ""
echo "  2. Test HTTPS:"
echo "     curl https://$DOMAIN/health"
echo ""
echo "  3. Test certificate renewal (dry run):"
echo "     certbot renew --dry-run"
echo ""
echo "=========================================="
