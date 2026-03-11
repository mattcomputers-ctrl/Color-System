# Deployment Guide — Ubuntu Server

## Prerequisites

- Ubuntu Server 22.04 LTS or later
- Root or sudo access
- At least 2 GB RAM, 10 GB disk space
- Network access for package installation

## Automated Setup

The fastest way to deploy is the automated setup script:

```bash
sudo bash scripts/setup_ubuntu.sh
```

This will install all dependencies, configure the database, build the frontend,
and set up Nginx + Gunicorn as system services.

## Manual Setup

### 1. Install System Packages

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib libpq-dev \
    nginx curl git build-essential \
    libxml2-dev libxslt-dev

# Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash -
sudo apt install -y nodejs
```

### 2. Create Database

```bash
sudo -u postgres psql
CREATE USER colorformulation WITH PASSWORD 'your-secure-password';
CREATE DATABASE colorformulation OWNER colorformulation;
\q
```

### 3. Backend Setup

```bash
cd /opt/colorformulation/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials and secret keys

# Initialize database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Load seed data
python seed.py
```

### 4. Frontend Build

```bash
cd /opt/colorformulation/frontend
npm install
echo "REACT_APP_API_URL=/api/v1" > .env
npm run build
```

### 5. Gunicorn Service

Create `/etc/systemd/system/colorformulation.service`:

```ini
[Unit]
Description=Color Formulation System
After=network.target postgresql.service

[Service]
Type=notify
User=colorformulation
WorkingDirectory=/opt/colorformulation/backend
Environment="PATH=/opt/colorformulation/backend/venv/bin:/usr/bin"
ExecStart=/opt/colorformulation/backend/venv/bin/gunicorn \
    --workers 4 --bind 127.0.0.1:5000 --timeout 120 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable colorformulation
sudo systemctl start colorformulation
```

### 6. Nginx Configuration

Create `/etc/nginx/sites-available/colorformulation` with the API proxy
and static file serving configuration (see setup script for full example).

### 7. SSL (Recommended)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Backups

Run the backup script regularly:

```bash
sudo bash scripts/backup.sh
```

Add to cron for daily backups:

```bash
echo "0 2 * * * root /opt/colorformulation/scripts/backup.sh" | sudo tee /etc/cron.d/colorformulation-backup
```

## Restore from Backup

```bash
# Restore database
gunzip -c /var/backups/colorformulation/db_TIMESTAMP.sql.gz | sudo -u postgres psql colorformulation

# Restore uploads
tar xzf /var/backups/colorformulation/uploads_TIMESTAMP.tar.gz -C /var/lib/colorformulation/
```

## Monitoring

```bash
# Service status
sudo systemctl status colorformulation

# Live logs
sudo journalctl -u colorformulation -f

# Application logs
tail -f /var/log/colorformulation/app.log
```

## Updating

```bash
cd /opt/colorformulation
git pull

# Backend
cd backend
source venv/bin/activate
pip install -r requirements.txt
flask db upgrade
deactivate

# Frontend
cd ../frontend
npm install
npm run build

# Restart
sudo systemctl restart colorformulation
```
