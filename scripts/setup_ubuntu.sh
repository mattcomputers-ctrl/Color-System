#!/usr/bin/env bash
# =============================================================================
# Color Formulation System — Full Automated Installer for Ubuntu Server
# =============================================================================
#
# This script performs a COMPLETE installation on a fresh Ubuntu Server 22.04+.
# It handles EVERYTHING — no manual steps required.
#
# What it does:
#   1.  Updates the system and installs all packages
#       (Python 3, Node.js 18, PostgreSQL, Nginx, build tools)
#   2.  Creates a dedicated system user and all directories
#   3.  Starts and configures PostgreSQL with a secure random password
#   4.  Clones or copies the application code to /opt/colorformulation
#   5.  Creates a Python virtual environment and installs all dependencies
#   6.  Generates all secret keys automatically
#   7.  Writes the complete production .env configuration
#   8.  Runs database migrations and loads seed data
#   9.  Builds the React frontend production bundle
#   10. Configures Gunicorn as a systemd service
#   11. Configures Nginx as a reverse proxy
#   12. Enables the firewall (UFW) with SSH + HTTP + HTTPS
#   13. Sets up daily automated backups via cron
#   14. Saves all generated credentials to a secure file
#   15. Runs verification checks on all services
#
# Usage (from within the cloned repo):
#   sudo bash scripts/setup_ubuntu.sh
#
# Prerequisites:
#   - Fresh Ubuntu Server 22.04 LTS or 24.04 LTS
#   - Root or sudo access
#   - Internet connectivity
#
# =============================================================================

set -euo pipefail

# ---- Configuration ----
APP_USER="colorformulation"
APP_DIR="/opt/colorformulation"
DB_NAME="colorformulation"
DB_USER="colorformulation"
UPLOAD_DIR="/var/lib/colorformulation/uploads"
LOG_DIR="/var/log/colorformulation"
BACKUP_DIR="/var/backups/colorformulation"
CREDENTIALS_FILE="/root/.colorformulation_credentials"

# Generate secure random values (URL-safe characters only)
DB_PASS="$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)"
SECRET_KEY="$(openssl rand -base64 48 | tr -d '/+=' | head -c 64)"
JWT_SECRET="$(openssl rand -base64 48 | tr -d '/+=' | head -c 64)"

# ---- Preflight checks ----
if [[ $EUID -ne 0 ]]; then
    echo "ERROR: This script must be run as root."
    echo "Usage: sudo bash $0"
    exit 1
fi

echo ""
echo "============================================================"
echo "  Color Formulation System — Full Automated Installer"
echo "============================================================"
echo ""
echo "  Target: $(lsb_release -ds 2>/dev/null || cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '"')"
echo "  This will install and configure the complete system."
echo "  Estimated time: 5-15 minutes."
echo ""
echo "============================================================"
echo ""

# ============================================================================
# STEP 1: System update and packages
# ============================================================================
echo "[1/12] Updating system and installing packages..."
export DEBIAN_FRONTEND=noninteractive

apt-get update -qq
apt-get upgrade -y -qq

apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    postgresql \
    postgresql-contrib \
    libpq-dev \
    nginx \
    curl \
    wget \
    git \
    rsync \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    openssl \
    ca-certificates \
    gnupg \
    ufw

echo "  System packages installed."

# ============================================================================
# STEP 2: Install Node.js 18 LTS
# ============================================================================
echo "[2/12] Installing Node.js 18 LTS..."
if command -v node &> /dev/null && [[ $(node -v | cut -d. -f1 | tr -d v) -ge 18 ]]; then
    echo "  Node.js $(node -v) already present — skipping."
else
    curl -fsSL https://deb.nodesource.com/setup_18.x 2>/dev/null | bash - > /dev/null 2>&1
    apt-get install -y -qq nodejs
    echo "  Node.js $(node -v) installed."
fi

# ============================================================================
# STEP 3: Start and configure PostgreSQL
# ============================================================================
echo "[3/12] Configuring PostgreSQL..."
systemctl start postgresql
systemctl enable postgresql > /dev/null 2>&1

# Create user (or update password if exists)
if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1; then
    sudo -u postgres psql -c "ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASS}';" > /dev/null 2>&1
    echo "  Database user '${DB_USER}' — password updated."
else
    sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';" > /dev/null 2>&1
    echo "  Database user '${DB_USER}' created."
fi

# Create database
if sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
    echo "  Database '${DB_NAME}' already exists."
else
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};" > /dev/null 2>&1
    echo "  Database '${DB_NAME}' created."
fi

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};" > /dev/null 2>&1

# ============================================================================
# STEP 4: Create system user and directories
# ============================================================================
echo "[4/12] Creating system user and directories..."
if ! id "${APP_USER}" &>/dev/null; then
    useradd --system --create-home --shell /bin/bash "${APP_USER}"
    echo "  System user '${APP_USER}' created."
else
    echo "  System user '${APP_USER}' already exists."
fi

mkdir -p "${APP_DIR}" "${UPLOAD_DIR}" "${LOG_DIR}" "${BACKUP_DIR}"
chown -R "${APP_USER}:${APP_USER}" "${UPLOAD_DIR}" "${LOG_DIR}" "${BACKUP_DIR}"

# ============================================================================
# STEP 5: Deploy application code
# ============================================================================
echo "[5/12] Deploying application code..."

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "${SCRIPT_PATH}")"

# Detect if we're inside the repo (has backend/ and frontend/ beside us)
if [[ -d "${REPO_ROOT}/backend/app" && -d "${REPO_ROOT}/frontend/src" ]]; then
    echo "  Copying from local source: ${REPO_ROOT}"
    rsync -a \
        --exclude='.git' \
        --exclude='node_modules' \
        --exclude='venv' \
        --exclude='.venv' \
        --exclude='__pycache__' \
        --exclude='frontend/build' \
        --exclude='.env' \
        "${REPO_ROOT}/" "${APP_DIR}/"
else
    echo "  ERROR: Cannot find application source code."
    echo "  This script must be run from within the cloned repository."
    echo "  Expected: ${REPO_ROOT}/backend/app  and  ${REPO_ROOT}/frontend/src"
    exit 1
fi

chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
echo "  Application deployed to ${APP_DIR}"

# ============================================================================
# STEP 6: Set up Python virtual environment and install dependencies
# ============================================================================
echo "[6/12] Setting up Python backend..."
cd "${APP_DIR}/backend"

python3 -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate

pip install --upgrade pip > /dev/null 2>&1
echo "  Installing Python packages (this takes 1-2 minutes)..."
pip install -r requirements.txt 2>&1 | grep -E "^(Successfully|ERROR)" || true
echo "  Python packages installed."

# ============================================================================
# STEP 7: Write production .env configuration
# ============================================================================
echo "[7/12] Writing production configuration..."
cat > "${APP_DIR}/backend/.env" <<ENVEOF
# Color Formulation System — Production Configuration
# Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
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

chmod 600 "${APP_DIR}/backend/.env"
chown "${APP_USER}:${APP_USER}" "${APP_DIR}/backend/.env"

# ============================================================================
# STEP 8: Initialize database — migrations and seed data
# ============================================================================
echo "[8/12] Initializing database..."
cd "${APP_DIR}/backend"
export FLASK_APP=wsgi.py
export FLASK_ENV=production

# Ensure the migrations/versions directory exists
mkdir -p "${APP_DIR}/backend/migrations/versions"

# Initialize Alembic if not already done
flask db init > /dev/null 2>&1 || true

# Generate initial migration and apply
echo "  Running migrations..."
flask db migrate -m "Initial schema" > /dev/null 2>&1 || true
flask db upgrade 2>&1 | grep -v "^$" || true
echo "  Database tables created."

echo "  Loading seed data..."
python seed.py
echo "  Seed data loaded."

deactivate
unset FLASK_APP FLASK_ENV

# ============================================================================
# STEP 9: Build the React frontend
# ============================================================================
echo "[9/12] Building frontend (this takes 1-3 minutes)..."
cd "${APP_DIR}/frontend"
echo "REACT_APP_API_URL=/api/v1" > .env

npm install --silent 2>&1 | tail -3
echo "  Node modules installed."

npm run build 2>&1 | tail -3
echo "  Frontend build complete."

chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

# ============================================================================
# STEP 10: Configure Gunicorn systemd service
# ============================================================================
echo "[10/12] Configuring Gunicorn service..."

# Calculate worker count: 2 * CPU + 1, clamped to [2, 8]
CPUS=$(nproc)
WORKERS=$(( CPUS * 2 + 1 ))
(( WORKERS < 2 )) && WORKERS=2
(( WORKERS > 8 )) && WORKERS=8

cat > /etc/systemd/system/colorformulation.service <<SVCEOF
[Unit]
Description=Color Formulation System (Gunicorn)
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=exec
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}/backend
Environment="PATH=${APP_DIR}/backend/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="FLASK_APP=wsgi.py"
Environment="FLASK_ENV=production"
ExecStart=${APP_DIR}/backend/venv/bin/gunicorn \\
    --workers ${WORKERS} \\
    --bind 127.0.0.1:5000 \\
    --timeout 120 \\
    --access-logfile ${LOG_DIR}/access.log \\
    --error-logfile ${LOG_DIR}/error.log \\
    wsgi:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable colorformulation > /dev/null 2>&1
systemctl start colorformulation
echo "  Gunicorn service started (${WORKERS} workers on ${CPUS} CPU cores)."

# Give Gunicorn a moment to bind
sleep 3

if ! systemctl is-active --quiet colorformulation; then
    echo ""
    echo "  WARNING: Gunicorn failed to start. Log output:"
    journalctl -u colorformulation -n 30 --no-pager
    echo ""
fi

# ============================================================================
# STEP 11: Configure Nginx reverse proxy
# ============================================================================
echo "[11/12] Configuring Nginx..."

cat > /etc/nginx/sites-available/colorformulation <<'NGXEOF'
server {
    listen 80;
    server_name _;

    # React frontend
    root /opt/colorformulation/frontend/build;
    index index.html;

    # API proxy to Gunicorn
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
        client_max_body_size 16M;
    }

    # SPA fallback — serve index.html for all non-file routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Security
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    server_tokens off;
}
NGXEOF

ln -sf /etc/nginx/sites-available/colorformulation /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t > /dev/null 2>&1
systemctl enable nginx > /dev/null 2>&1
systemctl reload nginx
echo "  Nginx configured and running."

# ============================================================================
# STEP 12: Firewall, backups, credentials, verification
# ============================================================================
echo "[12/12] Firewall, backups, and final checks..."

# ---- Firewall ----
ufw --force reset > /dev/null 2>&1
ufw default deny incoming > /dev/null 2>&1
ufw default allow outgoing > /dev/null 2>&1
ufw allow OpenSSH > /dev/null 2>&1
ufw allow "Nginx Full" > /dev/null 2>&1
ufw --force enable > /dev/null 2>&1
echo "  Firewall enabled (SSH + HTTP + HTTPS)."

# ---- Backup cron ----
chmod +x "${APP_DIR}/scripts/backup.sh" 2>/dev/null || true
cat > /etc/cron.d/colorformulation-backup <<CRONEOF
# Color Formulation System — Daily backup at 2:00 AM
0 2 * * * root ${APP_DIR}/scripts/backup.sh ${BACKUP_DIR} >> ${LOG_DIR}/backup.log 2>&1
CRONEOF
echo "  Daily backup scheduled (2:00 AM -> ${BACKUP_DIR})."

# ---- Save credentials ----
SERVER_IP="$(hostname -I | awk '{print $1}')"

cat > "${CREDENTIALS_FILE}" <<CREDEOF
# =============================================================
# Color Formulation System — Installation Credentials
# Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# =============================================================
#
# KEEP THIS FILE SECURE — it contains all system passwords.
#
# Application URL:  http://${SERVER_IP}
#
# Admin Login:
#   Email:     admin@colorformulation.local
#   Password:  ChangeMe123!
#
# Formulator Login:
#   Email:     formulator@colorformulation.local
#   Password:  ChangeMe123!
#
# Database:
#   Host:      localhost:5432
#   Name:      ${DB_NAME}
#   User:      ${DB_USER}
#   Password:  ${DB_PASS}
#
# Flask Secret Key:
#   ${SECRET_KEY}
#
# JWT Secret Key:
#   ${JWT_SECRET}
#
# Paths:
#   App:       ${APP_DIR}
#   Config:    ${APP_DIR}/backend/.env
#   Uploads:   ${UPLOAD_DIR}
#   Logs:      ${LOG_DIR}
#   Backups:   ${BACKUP_DIR}
#
# =============================================================
CREDEOF
chmod 600 "${CREDENTIALS_FILE}"

# ---- Verification ----
echo ""
echo "  Running verification checks..."
echo ""

ALL_OK=true

check_service() {
    local name="$1"
    local label="$2"
    if systemctl is-active --quiet "$name"; then
        printf "    %-24s OK\n" "${label}"
    else
        printf "    %-24s FAILED\n" "${label}"
        ALL_OK=false
    fi
}

check_service postgresql      "PostgreSQL"
check_service colorformulation "Gunicorn"
check_service nginx            "Nginx"

if ufw status | grep -q "Status: active"; then
    printf "    %-24s OK\n" "Firewall (UFW)"
else
    printf "    %-24s FAILED\n" "Firewall (UFW)"
    ALL_OK=false
fi

# Test the API responds
sleep 1
API_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/api/v1/auth/me 2>/dev/null || echo "000")
if [[ "$API_CODE" == "401" ]]; then
    printf "    %-24s OK\n" "API (auth check)"
else
    printf "    %-24s FAILED (HTTP ${API_CODE})\n" "API (auth check)"
    ALL_OK=false
fi

# Test the frontend responds
FE_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/ 2>/dev/null || echo "000")
if [[ "$FE_CODE" == "200" ]]; then
    printf "    %-24s OK\n" "Frontend"
else
    printf "    %-24s FAILED (HTTP ${FE_CODE})\n" "Frontend"
    ALL_OK=false
fi

# ---- Final output ----
echo ""
echo "============================================================"
if $ALL_OK; then
    echo "  INSTALLATION COMPLETE — ALL CHECKS PASSED"
else
    echo "  INSTALLATION COMPLETE — SOME CHECKS FAILED (see above)"
fi
echo "============================================================"
echo ""
echo "  Open in your browser:"
echo ""
echo "    http://${SERVER_IP}"
echo ""
echo "  Login:"
echo "    Email:     admin@colorformulation.local"
echo "    Password:  ChangeMe123!"
echo ""
echo "  Credentials saved to:"
echo "    ${CREDENTIALS_FILE}"
echo ""
echo "  Service commands:"
echo "    systemctl status colorformulation"
echo "    systemctl restart colorformulation"
echo "    journalctl -u colorformulation -f"
echo ""
echo "  IMPORTANT: Change the admin password after first login!"
echo ""
echo "  Optional — add HTTPS:"
echo "    apt install -y certbot python3-certbot-nginx"
echo "    certbot --nginx -d yourdomain.com"
echo ""
echo "============================================================"
