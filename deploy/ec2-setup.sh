#!/bin/bash
# =============================================================================
# A2A SNS System - EC2 Setup Script
# =============================================================================
# Usage:
#   1. Launch EC2 (Amazon Linux 2023 or Ubuntu 22.04)
#   2. SSH into EC2
#   3. Run: curl -sSL https://raw.githubusercontent.com/.../ec2-setup.sh | bash
#   Or: scp this file to EC2 and run: bash ec2-setup.sh
# =============================================================================

set -e

echo "=========================================="
echo "A2A SNS System - EC2 Setup"
echo "=========================================="

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Cannot detect OS"
    exit 1
fi

echo "Detected OS: $OS"

# =============================================================================
# 1. System Update & Basic Tools
# =============================================================================
echo ""
echo "[1/6] Installing system dependencies..."

if [ "$OS" = "amzn" ]; then
    # Amazon Linux 2023
    sudo dnf update -y
    sudo dnf install -y git curl wget unzip htop tmux jq
elif [ "$OS" = "ubuntu" ]; then
    # Ubuntu
    sudo apt-get update
    sudo apt-get install -y git curl wget unzip htop tmux jq
fi

# =============================================================================
# 2. Install Docker
# =============================================================================
echo ""
echo "[2/6] Installing Docker..."

if [ "$OS" = "amzn" ]; then
    sudo dnf install -y docker
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker $USER
elif [ "$OS" = "ubuntu" ]; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker $USER
fi

# Install Docker Compose
echo "Installing Docker Compose..."
DOCKER_COMPOSE_VERSION="v2.24.0"
sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# =============================================================================
# 3. Install Node.js (for Claude Code)
# =============================================================================
echo ""
echo "[3/6] Installing Node.js..."

if [ "$OS" = "amzn" ]; then
    curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
    sudo dnf install -y nodejs
elif [ "$OS" = "ubuntu" ]; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

echo "Node.js version: $(node --version)"
echo "npm version: $(npm --version)"

# =============================================================================
# 4. Install Python 3.11+
# =============================================================================
echo ""
echo "[4/6] Installing Python..."

if [ "$OS" = "amzn" ]; then
    sudo dnf install -y python3.11 python3.11-pip
    sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
elif [ "$OS" = "ubuntu" ]; then
    sudo apt-get install -y python3 python3-pip python3-venv
fi

echo "Python version: $(python3 --version)"

# =============================================================================
# 5. Install Claude Code CLI
# =============================================================================
echo ""
echo "[5/6] Installing Claude Code CLI..."

sudo npm install -g @anthropic-ai/claude-code

echo "Claude Code version: $(claude --version 2>/dev/null || echo 'installed')"

# =============================================================================
# 6. Setup Project Directory
# =============================================================================
echo ""
echo "[6/6] Setting up project directory..."

# Create app directory
sudo mkdir -p /opt/a2a-sns
sudo chown $USER:$USER /opt/a2a-sns

# Create systemd service for A2A
sudo tee /etc/systemd/system/a2a-sns.service > /dev/null <<EOF
[Unit]
Description=A2A SNS Agent System
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/a2a-sns
ExecStart=/usr/local/bin/docker-compose up
ExecStop=/usr/local/bin/docker-compose down
Restart=always
RestartSec=10
User=$USER

[Install]
WantedBy=multi-user.target
EOF

# =============================================================================
# Complete
# =============================================================================
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo ""
echo "1. Re-login to apply docker group:"
echo "   exit && ssh <your-ec2>"
echo ""
echo "2. Login to Claude Code:"
echo "   claude login"
echo ""
echo "3. Clone your A2A SNS repository:"
echo "   cd /opt/a2a-sns"
echo "   git clone <your-repo-url> ."
echo ""
echo "4. Start the system:"
echo "   docker-compose up -d"
echo ""
echo "5. (Optional) Enable auto-start on boot:"
echo "   sudo systemctl enable a2a-sns"
echo ""
echo "=========================================="
