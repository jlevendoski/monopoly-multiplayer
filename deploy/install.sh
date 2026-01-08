#!/bin/bash
# Monopoly Server Installation Script
# Run as 'monopoly' user from /opt/monopoly

set -e

echo "=========================================="
echo " Monopoly Server Installation"
echo "=========================================="

APP_DIR="/opt/monopoly"
cd $APP_DIR

# Create virtual environment
echo ""
echo "[1/4] Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo ""
echo "[2/4] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements-server.txt

# Create data directory
echo ""
echo "[3/4] Creating data directory..."
mkdir -p data
touch data/.gitkeep

# Create environment file if not exists
echo ""
echo "[4/4] Creating environment configuration..."
if [ ! -f .env ]; then
    cat > .env << EOF
# Monopoly Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8765
DATABASE_PATH=/opt/monopoly/data/monopoly.db
LOG_LEVEL=INFO
SERVER_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
EOF
    echo "Created .env file with auto-generated secret key"
else
    echo ".env file already exists"
fi

echo ""
echo "=========================================="
echo " Installation Complete!"
echo "=========================================="
echo ""
echo "Test the server manually:"
echo "  source venv/bin/activate"
echo "  python -m server.main"
echo ""
echo "Then set up the systemd service as root."
echo "=========================================="
