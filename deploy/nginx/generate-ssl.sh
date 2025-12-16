#!/bin/bash
# =============================================================================
# Generate Self-Signed SSL Certificates for Development
# =============================================================================
# For production, use Let's Encrypt or a proper CA
# =============================================================================

set -e

SSL_DIR="$(dirname "$0")/ssl"
mkdir -p "$SSL_DIR"

# Check if certificates already exist
if [ -f "$SSL_DIR/cert.pem" ] && [ -f "$SSL_DIR/key.pem" ]; then
    echo "SSL certificates already exist in $SSL_DIR"
    echo "Delete them first if you want to regenerate."
    exit 0
fi

echo "Generating self-signed SSL certificates..."

# Generate private key and certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$SSL_DIR/key.pem" \
    -out "$SSL_DIR/cert.pem" \
    -subj "/C=JP/ST=Tokyo/L=Tokyo/O=A2A-SNS/OU=Development/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,DNS:*.localhost,IP:127.0.0.1"

# Set permissions
chmod 600 "$SSL_DIR/key.pem"
chmod 644 "$SSL_DIR/cert.pem"

echo ""
echo "=========================================="
echo "SSL Certificates Generated"
echo "=========================================="
echo "Certificate: $SSL_DIR/cert.pem"
echo "Private Key: $SSL_DIR/key.pem"
echo ""
echo "WARNING: These are self-signed certificates."
echo "For production, use Let's Encrypt:"
echo "  certbot certonly --standalone -d your-domain.com"
echo "=========================================="
