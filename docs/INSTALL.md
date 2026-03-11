# Color Formulation System — Full Ubuntu Server Installation Guide

Step-by-step instructions for installing on a **fresh Ubuntu Server 22.04 LTS** (or 24.04 LTS).

All commands are run as root unless noted otherwise. If you are logged in as a regular user, prefix commands with `sudo` or run `sudo -i` first.

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Update the System](#2-update-the-system)
3. [Install System Dependencies](#3-install-system-dependencies)
4. [Install Node.js 18 LTS](#4-install-nodejs-18-lts)
5. [Install and Configure PostgreSQL](#5-install-and-configure-postgresql)
6. [Create Application User and Directories](#6-create-application-user-and-directories)
7. [Clone the Application](#7-clone-the-application)
8. [Set Up the Backend (Python/Flask)](#8-set-up-the-backend-pythonflask)
9. [Configure Environment Variables](#9-configure-environment-variables)
10. [Initialize the Database](#10-initialize-the-database)
11. [Load Seed Data](#11-load-seed-data)
12. [Build the Frontend (React)](#12-build-the-frontend-react)
13. [Configure Gunicorn (Application Server)](#13-configure-gunicorn-application-server)
14. [Configure Nginx (Web Server / Reverse Proxy)](#14-configure-nginx-web-server--reverse-proxy)
15. [Configure Firewall](#15-configure-firewall)
16. [Start Everything and Verify](#16-start-everything-and-verify)
17. [Set Up SSL with Let's Encrypt (Optional but Recommended)](#17-set-up-ssl-with-lets-encrypt-optional-but-recommended)
18. [Set Up Automated Backups](#18-set-up-automated-backups)
19. [Post-Install Tasks](#19-post-install-tasks)
20. [Troubleshooting](#20-troubleshooting)

---

## 1. System Requirements

| Resource       | Minimum       | Recommended     |
|----------------|---------------|-----------------|
| OS             | Ubuntu 22.04  | Ubuntu 24.04    |
| CPU            | 1 core        | 2+ cores        |
| RAM            | 2 GB          | 4 GB            |
| Disk           | 10 GB         | 20+ GB          |
| Network        | Internet access for package install | Static IP or DNS name |

---

## 2. Update the System

```bash
apt update && apt upgrade -y
reboot    # If kernel was updated
```

After reboot, log back in and become root:

```bash
sudo -i
```

---

## 3. Install System Dependencies

```bash
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    postgresql \
    postgresql-contrib \
    libpq-dev \
    nginx \
    curl \
    git \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    openssl \
    ufw
```

Verify Python is installed:

```bash
python3 --version
# Should show Python 3.10+ (Ubuntu 22.04 ships 3.10, Ubuntu 24.04 ships 3.12)
```

---

## 4. Install Node.js 18 LTS

Ubuntu's default Node.js is too old. Install Node.js 18 from NodeSource:

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs
```

Verify:

```bash
node --version
# Should show v18.x.x

npm --version
# Should show 9.x.x or 10.x.x
```

---

## 5. Install and Configure PostgreSQL

PostgreSQL was installed in step 3. Now create the database and user.

### 5.1. Verify PostgreSQL is running

```bash
systemctl status postgresql
```

You should see `active (exited)` or `active (running)`. If not:

```bash
systemctl start postgresql
systemctl enable postgresql
```

### 5.2. Generate a secure database password

Generate and save a password. You will need it in step 9.

```bash
DB_PASS=$(openssl rand -base64 24)
echo "Database password: $DB_PASS"
echo "SAVE THIS PASSWORD — you will need it for the .env file"
```

### 5.3. Create the database user and database

```bash
sudo -u postgres psql <<EOF
CREATE USER colorformulation WITH PASSWORD '${DB_PASS}';
CREATE DATABASE colorformulation OWNER colorformulation;
GRANT ALL PRIVILEGES ON DATABASE colorformulation TO colorformulation;
EOF
```

### 5.4. Verify the database connection

```bash
sudo -u postgres psql -c "\l" | grep colorformulation
```

You should see a line showing the `colorformulation` database owned by `colorformulation`.

---

## 6. Create Application User and Directories

Create a dedicated system user (no login shell for security):

```bash
useradd --system --create-home --shell /bin/bash colorformulation
```

Create the required directories:

```bash
mkdir -p /opt/colorformulation
mkdir -p /var/lib/colorformulation/uploads
mkdir -p /var/log/colorformulation

chown -R colorformulation:colorformulation /opt/colorformulation
chown -R colorformulation:colorformulation /var/lib/colorformulation
chown -R colorformulation:colorformulation /var/log/colorformulation
```

---

## 7. Clone the Application

```bash
cd /opt/colorformulation
git clone https://github.com/mattcomputers-ctrl/Color-System.git .
```

> **Note:** If the repo is private, you will need to configure git credentials or use an SSH key first.

Set ownership:

```bash
chown -R colorformulation:colorformulation /opt/colorformulation
```

---

## 8. Set Up the Backend (Python/Flask)

### 8.1. Create a Python virtual environment

```bash
cd /opt/colorformulation/backend
python3 -m venv venv
```

### 8.2. Activate the virtual environment

```bash
source venv/bin/activate
```

Your prompt should now show `(venv)` at the beginning.

### 8.3. Upgrade pip

```bash
pip install --upgrade pip
```

### 8.4. Install Python dependencies

```bash
pip install -r requirements.txt
```

This installs Flask, SQLAlchemy, NumPy, SciPy, lxml, ReportLab, and all other backend packages. It may take 2-3 minutes.

### 8.5. Verify the install

```bash
python -c "import flask; import numpy; import scipy; import lxml; print('All packages OK')"
```

**Do not deactivate the virtual environment yet** — you need it for steps 9-11.

---

## 9. Configure Environment Variables

### 9.1. Generate secret keys

```bash
SECRET_KEY=$(openssl rand -base64 48)
JWT_SECRET=$(openssl rand -base64 48)

echo "SECRET_KEY: $SECRET_KEY"
echo "JWT_SECRET: $JWT_SECRET"
```

### 9.2. Create the .env file

Replace `YOUR_DB_PASSWORD_HERE` with the database password you generated in step 5.2:

```bash
cat > /opt/colorformulation/backend/.env <<'ENVFILE'
# Database
DATABASE_URL=postgresql://colorformulation:YOUR_DB_PASSWORD_HERE@localhost:5432/colorformulation

# Flask
FLASK_APP=wsgi.py
FLASK_ENV=production
SECRET_KEY=REPLACE_WITH_SECRET_KEY
JWT_SECRET_KEY=REPLACE_WITH_JWT_SECRET

# JWT token lifetime in seconds (3600 = 1 hour)
JWT_ACCESS_TOKEN_EXPIRES=3600

# File uploads
UPLOAD_FOLDER=/var/lib/colorformulation/uploads
MAX_CONTENT_LENGTH=16777216

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/colorformulation/app.log
ENVFILE
```

### 9.3. Edit the .env file with your actual values

```bash
nano /opt/colorformulation/backend/.env
```

Replace these three placeholders with the real values you generated:
- `YOUR_DB_PASSWORD_HERE` → the database password from step 5.2
- `REPLACE_WITH_SECRET_KEY` → the SECRET_KEY from step 9.1
- `REPLACE_WITH_JWT_SECRET` → the JWT_SECRET from step 9.1

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

### 9.4. Secure the .env file

```bash
chmod 600 /opt/colorformulation/backend/.env
chown colorformulation:colorformulation /opt/colorformulation/backend/.env
```

---

## 10. Initialize the Database

Make sure you are still in the backend directory with the venv activated:

```bash
cd /opt/colorformulation/backend
source venv/bin/activate   # if not already active
```

### 10.1. Initialize Alembic migrations

```bash
export FLASK_APP=wsgi.py
flask db init
```

### 10.2. Generate the initial migration

```bash
flask db migrate -m "Initial migration"
```

### 10.3. Apply the migration (create all tables)

```bash
flask db upgrade
```

### 10.4. Verify tables were created

```bash
sudo -u postgres psql -d colorformulation -c "\dt"
```

You should see tables like `users`, `roles`, `ink_series`, `mixing_bases`, `pantone_targets`, etc.

---

## 11. Load Seed Data

This creates the default admin user, sample roles, example ink series, synthetic mixing bases, and sample Pantone targets:

```bash
cd /opt/colorformulation/backend
python seed.py
```

Expected output:

```
Seeding database...
  Created admin user: admin@colorformulation.local / ChangeMe123!
  Created formulator user
  Created base UV-OFFSET/W (White) L*=91.2 a*=-0.8 b*=1.5
  Created base UV-OFFSET/Y (Yellow) L*=82.3 a*=-3.1 b*=78.9
  ...
  Created Pantone target: 185 C
  Created Pantone target: 286 C
  ...
Seed data loaded successfully.
```

Now deactivate the virtual environment:

```bash
deactivate
```

---

## 12. Build the Frontend (React)

### 12.1. Navigate to the frontend directory

```bash
cd /opt/colorformulation/frontend
```

### 12.2. Set the API URL

```bash
echo "REACT_APP_API_URL=/api/v1" > .env
```

### 12.3. Install Node.js dependencies

```bash
npm install
```

This will take 1-3 minutes depending on your server speed.

### 12.4. Build the production bundle

```bash
npm run build
```

This compiles the React app into static files in the `build/` directory. Takes 1-2 minutes.

### 12.5. Verify the build

```bash
ls -la build/
```

You should see `index.html`, `static/`, and other files.

### 12.6. Set ownership

```bash
chown -R colorformulation:colorformulation /opt/colorformulation
```

---

## 13. Configure Gunicorn (Application Server)

Gunicorn serves the Flask backend. We run it as a systemd service.

### 13.1. Create the systemd service file

```bash
cat > /etc/systemd/system/colorformulation.service <<'EOF'
[Unit]
Description=Color Formulation System
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=notify
User=colorformulation
Group=colorformulation
WorkingDirectory=/opt/colorformulation/backend
Environment="PATH=/opt/colorformulation/backend/venv/bin:/usr/bin"
ExecStart=/opt/colorformulation/backend/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:5000 \
    --timeout 120 \
    --access-logfile /var/log/colorformulation/access.log \
    --error-logfile /var/log/colorformulation/error.log \
    wsgi:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

> **Note:** `--workers 4` is good for a 2-core server. Use `2 * CPU cores + 1` as a guideline.

### 13.2. Reload systemd, enable, and start the service

```bash
systemctl daemon-reload
systemctl enable colorformulation
systemctl start colorformulation
```

### 13.3. Verify it is running

```bash
systemctl status colorformulation
```

You should see `active (running)`. If it says `failed`, check the logs:

```bash
journalctl -u colorformulation -n 50 --no-pager
```

### 13.4. Test the backend directly

```bash
curl -s http://127.0.0.1:5000/api/v1/auth/login | head
```

You should get a JSON response (an error about missing body is fine — it means the server is responding).

---

## 14. Configure Nginx (Web Server / Reverse Proxy)

Nginx serves the React frontend and proxies API requests to Gunicorn.

### 14.1. Create the Nginx site configuration

```bash
cat > /etc/nginx/sites-available/colorformulation <<'EOF'
server {
    listen 80;
    server_name _;

    # Frontend static files (React build)
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
        client_max_body_size 16M;
    }

    # React SPA — serve index.html for all non-file routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Security headers
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
EOF
```

### 14.2. Enable the site and disable the default

```bash
ln -sf /etc/nginx/sites-available/colorformulation /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
```

### 14.3. Test the Nginx configuration

```bash
nginx -t
```

Should say `syntax is ok` and `test is successful`.

### 14.4. Reload Nginx

```bash
systemctl reload nginx
```

---

## 15. Configure Firewall

```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable
ufw status
```

Expected output:

```
Status: active

To                         Action      From
--                         ------      ----
OpenSSH                    ALLOW       Anywhere
Nginx Full                 ALLOW       Anywhere
```

---

## 16. Start Everything and Verify

### 16.1. Check all services are running

```bash
systemctl status postgresql
systemctl status colorformulation
systemctl status nginx
```

All three should show `active`.

### 16.2. Get your server's IP address

```bash
hostname -I | awk '{print $1}'
```

### 16.3. Open in a web browser

Navigate to:

```
http://YOUR_SERVER_IP
```

You should see the Color Formulation System login page.

### 16.4. Log in with the default admin account

```
Email:    admin@colorformulation.local
Password: ChangeMe123!
```

### 16.5. Verify the dashboard loads

After login you should see the dashboard with statistics showing:
- 3 Ink Series
- 9 Mixing Bases
- 10 Pantone Targets
- 0 Pantone Formulas (none generated yet)

---

## 17. Set Up SSL with Let's Encrypt (Optional but Recommended)

If your server has a public DNS name:

### 17.1. Install Certbot

```bash
apt install -y certbot python3-certbot-nginx
```

### 17.2. Obtain and install the certificate

Replace `your-domain.com` with your actual domain:

```bash
certbot --nginx -d your-domain.com
```

Follow the prompts. Certbot will automatically configure Nginx for HTTPS.

### 17.3. Verify auto-renewal

```bash
certbot renew --dry-run
```

### 17.4. Update the Nginx config server_name

Edit `/etc/nginx/sites-available/colorformulation` and change `server_name _;` to:

```
server_name your-domain.com;
```

Then reload:

```bash
nginx -t && systemctl reload nginx
```

---

## 18. Set Up Automated Backups

### 18.1. Make the backup script executable

```bash
chmod +x /opt/colorformulation/scripts/backup.sh
```

### 18.2. Create the backup directory

```bash
mkdir -p /var/backups/colorformulation
```

### 18.3. Test the backup manually

```bash
bash /opt/colorformulation/scripts/backup.sh
```

### 18.4. Schedule daily backups via cron

```bash
cat > /etc/cron.d/colorformulation-backup <<'EOF'
# Run backup daily at 2:00 AM
0 2 * * * root /opt/colorformulation/scripts/backup.sh /var/backups/colorformulation >> /var/log/colorformulation/backup.log 2>&1
EOF
```

### 18.5. Verify cron is set

```bash
cat /etc/cron.d/colorformulation-backup
```

---

## 19. Post-Install Tasks

### 19.1. Change the admin password

Log in to the web UI and change the default admin password immediately.

### 19.2. Create user accounts

Go to **Admin > Users** and create accounts for your formulators and viewers.

### 19.3. Import your real mixing base data

For each ink series:
1. Go to **Ink Series** and select or create your series
2. Add your mixing bases (code, name, color index)
3. For each base, add concentration levels (e.g., 100% full strength)
4. Upload CXF files for each concentration level

### 19.4. Import Pantone target data

Go to **Pantone Targets** and either:
- Manually enter LAB values from your Pantone guide
- Upload CXF files with Pantone spectral data (if you have licensed Pantone digital data)

### 19.5. Test formula generation

1. Go to **Pantone > Generate Formula**
2. Select a Pantone target and ink series
3. Click **Generate Formula**
4. Review the result — check the Delta E value

---

## 20. Troubleshooting

### Service won't start

```bash
# View detailed error logs
journalctl -u colorformulation -n 100 --no-pager

# Check the application log
cat /var/log/colorformulation/app.log

# Test Flask directly
cd /opt/colorformulation/backend
source venv/bin/activate
flask run --host 0.0.0.0 --port 5001
# Then try: curl http://localhost:5001/api/v1/admin/dashboard-stats
```

### Database connection errors

```bash
# Verify PostgreSQL is running
systemctl status postgresql

# Test the connection manually
sudo -u postgres psql -d colorformulation -c "SELECT 1;"

# Check the DATABASE_URL in .env
cat /opt/colorformulation/backend/.env | grep DATABASE_URL

# Test from the app user
sudo -u colorformulation psql -h localhost -U colorformulation -d colorformulation -c "SELECT 1;"
```

### Nginx 502 Bad Gateway

This means Nginx can't reach Gunicorn:

```bash
# Is Gunicorn running?
systemctl status colorformulation

# Is it listening on port 5000?
ss -tlnp | grep 5000

# Restart if needed
systemctl restart colorformulation
```

### Frontend shows blank page

```bash
# Was the frontend built?
ls -la /opt/colorformulation/frontend/build/index.html

# If not, rebuild it:
cd /opt/colorformulation/frontend
npm run build
systemctl reload nginx
```

### Permission errors

```bash
# Fix ownership
chown -R colorformulation:colorformulation /opt/colorformulation
chown -R colorformulation:colorformulation /var/lib/colorformulation
chown -R colorformulation:colorformulation /var/log/colorformulation
```

### Migration errors

```bash
cd /opt/colorformulation/backend
source venv/bin/activate
export FLASK_APP=wsgi.py

# Check migration status
flask db current

# If migrations are corrupted, reinitialize:
# WARNING: This drops all data!
flask db stamp head
flask db migrate -m "Reinitialize"
flask db upgrade
python seed.py
```

### Check all ports

```bash
ss -tlnp
```

Expected:
- `5432` — PostgreSQL
- `5000` — Gunicorn (bound to 127.0.0.1 only)
- `80` — Nginx
- `443` — Nginx (if SSL configured)

---

## Quick Reference

| Item | Value |
|------|-------|
| Application directory | `/opt/colorformulation` |
| Backend config | `/opt/colorformulation/backend/.env` |
| Upload storage | `/var/lib/colorformulation/uploads` |
| Application logs | `/var/log/colorformulation/app.log` |
| Access logs | `/var/log/colorformulation/access.log` |
| Error logs | `/var/log/colorformulation/error.log` |
| Backup location | `/var/backups/colorformulation` |
| Service name | `colorformulation` |
| Default admin email | `admin@colorformulation.local` |
| Default admin password | `ChangeMe123!` |

### Service commands

```bash
systemctl start colorformulation      # Start the app
systemctl stop colorformulation       # Stop the app
systemctl restart colorformulation    # Restart the app
systemctl status colorformulation     # Check status
journalctl -u colorformulation -f     # Live logs
```

### Updating the application

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
systemctl restart colorformulation
systemctl reload nginx
```
