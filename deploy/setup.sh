#!/bin/bash
# Monopoly Server Setup Script for Ubuntu/Debian
# Run as root on a fresh server

set -e

echo "=========================================="
echo " Monopoly Server Setup"
echo "=========================================="

# Update system
echo ""
echo "[1/6] Updating system packages..."
apt update && apt upgrade -y

# Install Python 3.11+ and dependencies
echo ""
echo "[2/6] Installing Python and dependencies..."
apt install -y python3 python3-pip python3-venv git ufw

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $PYTHON_VERSION"

# Create monopoly user
echo ""
echo "[3/6] Creating monopoly user..."
if id "monopoly" &>/dev/null; then
    echo "User 'monopoly' already exists"
else
    useradd -m -s /bin/bash monopoly
    echo "Created user 'monopoly'"
fi

# Create app directory
echo ""
echo "[4/6] Setting up application directory..."
APP_DIR="/opt/monopoly"
mkdir -p $APP_DIR
chown monopoly:monopoly $APP_DIR

# Setup firewall
echo ""
echo "[5/6] Configuring firewall..."
ufw allow 22/tcp      # SSH
ufw allow 8765/tcp    # Monopoly WebSocket
ufw --force enable
ufw status

echo ""
echo "[6/6] Setup complete!"
echo ""
echo "=========================================="
echo " Next Steps"
echo "=========================================="
echo ""
echo "1. Copy your Monopoly code to: $APP_DIR"
echo "   scp -r Monopoly/* root@your-server:/opt/monopoly/"
echo ""
echo "2. Run the install script as monopoly user:"
echo "   su - monopoly"
echo "   cd /opt/monopoly"
echo "   ./deploy/install.sh"
echo ""
echo "3. Then as root, enable the service:"
echo "   cp /opt/monopoly/deploy/monopoly.service /etc/systemd/system/"
echo "   systemctl daemon-reload"
echo "   systemctl enable monopoly"
echo "   systemctl start monopoly"
echo ""
echo "=========================================="
