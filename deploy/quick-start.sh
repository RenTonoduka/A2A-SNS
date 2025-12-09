#!/bin/bash
# =============================================================================
# A2A SNS System - Quick Start Script (EC2)
# =============================================================================
# Run after ec2-setup.sh and claude login
# =============================================================================

set -e

PROJECT_DIR="/opt/a2a-sns"
cd $PROJECT_DIR

echo "=========================================="
echo "A2A SNS System - Quick Start"
echo "=========================================="

# Check Claude authentication
echo ""
echo "[1/4] Checking Claude Code authentication..."
if [ ! -d "$HOME/.claude" ]; then
    echo "ERROR: Claude Code not authenticated."
    echo "Please run: claude login"
    exit 1
fi
echo "Claude authentication: OK"

# Check Docker
echo ""
echo "[2/4] Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running or you don't have permission."
    echo "Try: sudo systemctl start docker"
    echo "Or re-login to apply docker group."
    exit 1
fi
echo "Docker: OK"

# Install Python dependencies
echo ""
echo "[3/4] Installing Python dependencies..."
pip3 install -q -r _shared/requirements.txt
echo "Python dependencies: OK"

# Start services
echo ""
echo "[4/4] Starting A2A services..."
docker-compose -f docker-compose.yml -f docker-compose.ec2.yml up -d --build

# Wait for services
echo ""
echo "Waiting for services to start..."
sleep 10

# Health check
echo ""
echo "=========================================="
echo "Service Status"
echo "=========================================="
docker-compose ps

echo ""
echo "=========================================="
echo "Health Check"
echo "=========================================="

check_service() {
    local name=$1
    local port=$2
    if curl -s "http://localhost:$port/.well-known/agent.json" > /dev/null 2>&1; then
        echo "  $name (port $port): UP"
    else
        echo "  $name (port $port): DOWN"
    fi
}

check_service "sns-orchestrator" 8080
check_service "youtube-script-writer" 8081
check_service "youtube-shorts-creator" 8082
check_service "youtube-seo-optimizer" 8083
check_service "youtube-thumbnail-planner" 8084

echo ""
echo "=========================================="
echo "Quick Start Complete!"
echo "=========================================="
echo ""
echo "Test command:"
echo '  curl http://localhost:8080/.well-known/agent.json | jq'
echo ""
echo "View logs:"
echo '  docker-compose logs -f'
echo ""
