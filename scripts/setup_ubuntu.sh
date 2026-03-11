#!/usr/bin/env bash
# =============================================================================
# Color Formulation System — Ubuntu Server Setup Script
# =============================================================================
# This script installs all prerequisites and configures the system for
# production deployment on Ubuntu Server 22.04+.
#
# Usage:
#   sudo bash scripts/setup_ubuntu.sh
#
# This script will:
#   1. Install system packages (Python, Node.js, PostgreSQL, Nginx)
#   2. Create a dedicated system user
#   3. Create the PostgreSQL database and user
#   4. Set up Python virtual environment and install dependencies
#   5. Build the frontend
#   6. Configure Nginx and Gunicorn as systemd services
#   7. Run database migrations and seed data
# =============================================================================

set -euo pipefail

APP_NAME="colorformulation"
APP_USER="colorformulation"
APP_DIR="/opt/colorformulation"
DB_NAME="colorformulation"
DB_USER="colorformulation"
DB_PASS=$(openssl rand -base64 24)
SECRET_KEY=$(openssl rand -base64 48)
JWT_SECRET=$(openssl rand -base64 48)
UPLOAD_DIR="/var/lib/colorformulation/uploads"
LOG_DIR="/var/log/colorformulation"

echo "============================================"
echo " Color Formulation System — Server Setup"
echo "============================================"
echo ""

# --- Step 1: System packages ---
echo "[1/8] Installing system packages..."
apt-get update -qq
apt-get install -y -qq \
    python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib libpq-dev \
    nginx \
    curl git build-essential \
    libxml2-dev libxslt-dev

# Install Node.js 18 LTS
if ! command -v node &> /dev/null || [[ $(node -v | cut -d. -f1 | tr -d v) -lt 18 ]]; then
    echo "  Installing Node.js 18..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt-get install -y -qq nodejs
fi

# --- Step 2: Create system user ---
echo "[2/8] Creating system user..."
if ! id "$APP_USER" &>/dev/null; then
    useradd --system --create-home --shell /bin/bash "$APP_USER"
fi

# --- Step 3: Create directories ---
echo "[3/8] Setting up directories..."
mkdir -p "$APP_DIR" "$UPLOAD_DIR" "$LOG_DIR"
chown -R "$APP_USER:$APP_USER" "$APP_DIR" "$UPLOAD_DIR" "$LOG_DIR"

# --- Step 4: PostgreSQL setup ---
echo "[4/8] Configuring PostgreSQL..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

# --- Step 5: Copy application files ---
echo "[5/8] Deploying application..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cp -r "$PROJECT_DIR/backend" "$APP_DIR/"
cp -r "$PROJECT_DIR/frontend" "$APP_DIR/"

# Create .env file
cat > "$APP_DIR/backend/.env" <<ENVEOF
DATABASE_URL=postgresql://${DB_USER}:${DB_PASS}@localhost:5432/${DB_NAME}
FLASK_APP=wsgi.py
FLASK_ENV=production
SECRET_KEY=${SECRET_KEY}
JWT_SECRET_KEY=${JWT_SECRET}
JWT_ACCESS_TOKEN_EXPIRES=3600
UPLOAD_FOLDER=${UPLOAD_DIR}
MAX_CONTENT_LENGTH=16777216
LOG_LEVEL=INFO
LOG_FILE=${LOG_DIR}/app.log
ENVEOF

# Python environment
echo "  Setting up Python environment..."
cd "$APP_DIR/backend"
python3 -m venv venv
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Run migrations and seed
echo "  Running database migrations..."
flask db upgrade 2>/dev/null || flask db init && flask db migrate -m "Initial" && flask db upgrade
echo "  Loading seed data..."
python seed.py

deactivate

# Build frontend
echo "[6/8] Building frontend..."
cd "$APP_DIR/frontend"
npm install --silent
echo "REACT_APP_API_URL=/api/v1" > .env
npm run build

chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# --- Step 7: Systemd service ---
echo "[7/8] Creating systemd service..."
cat > /etc/systemd/system/colorformulation.service <<SVCEOF
[Unit]
Description=Color Formulation System
After=network.target postgresql.service

[Service]
Type=notify
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}/backend
Environment="PATH=${APP_DIR}/backend/venv/bin:/usr/bin"
ExecStart=${APP_DIR}/backend/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:5000 \
    --timeout 120 \
    --access-logfile ${LOG_DIR}/access.log \
    --error-logfile ${LOG_DIR}/error.log \
    wsgi:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable colorformulation
systemctl start colorformulation

# --- Step 8: Nginx configuration ---
echo "[8/8] Configuring Nginx..."
cat > /etc/nginx/sites-available/colorformulation <<NGXEOF
server {
    listen 80;
    server_name _;

    # Frontend static files
    root ${APP_DIR}/frontend/build;
    index index.html;

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        client_max_body_size 16M;
    }

    # React SPA — serve index.html for all non-file routes
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
}
NGXEOF

ln -sf /etc/nginx/sites-available/colorformulation /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo ""
echo "============================================"
echo " Setup Complete!"
echo "============================================"
echo ""
echo " Application URL:  http://$(hostname -I | awk '{print $1}')"
echo " Admin login:      admin@colorformulation.local"
echo " Admin password:   ChangeMe123!"
echo ""
echo " Database name:    ${DB_NAME}"
echo " Database user:    ${DB_USER}"
echo " Database pass:    ${DB_PASS}"
echo ""
echo " Config file:      ${APP_DIR}/backend/.env"
echo " Upload directory: ${UPLOAD_DIR}"
echo " Log directory:    ${LOG_DIR}"
echo ""
echo " IMPORTANT: Change the admin password after first login!"
echo " IMPORTANT: Save the database password above securely!"
echo ""
echo " To check service status:  systemctl status colorformulation"
echo " To view logs:             journalctl -u colorformulation -f"
echo "============================================"
