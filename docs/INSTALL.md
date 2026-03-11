# Color Formulation System — Installation Guide

## Quick Install (Automated)

On a fresh Ubuntu Server 22.04+ with root access, run these three commands:

```bash
sudo -i
git clone https://github.com/mattcomputers-ctrl/Color-System.git /tmp/color-system
bash /tmp/color-system/scripts/setup_ubuntu.sh
```

The installer does everything automatically and takes 5-15 minutes. When finished
it prints the URL, login credentials, and saves all passwords to `/root/.colorformulation_credentials`.

See below for what the installer does, system requirements, and troubleshooting.

---

## System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| OS | Ubuntu Server 22.04 LTS | Ubuntu Server 24.04 LTS |
| CPU | 1 core | 2+ cores |
| RAM | 2 GB | 4 GB |
| Disk | 10 GB | 20+ GB |
| Network | Internet for package install | Static IP or DNS name |

---

## What the Installer Does

The `setup_ubuntu.sh` script performs all of these steps automatically:

| Step | Action |
|------|--------|
| 1 | Updates the system and installs all packages (Python 3, PostgreSQL, Nginx, build tools) |
| 2 | Installs Node.js 18 LTS from NodeSource |
| 3 | Starts PostgreSQL, creates the database user and database with a random password |
| 4 | Creates a `colorformulation` system user and all directories |
| 5 | Copies the application code to `/opt/colorformulation` |
| 6 | Creates a Python virtual environment, installs all pip packages |
| 7 | Generates secret keys and writes the production `.env` file |
| 8 | Runs database migrations (Flask-Migrate/Alembic) and loads seed data |
| 9 | Installs npm packages and builds the React frontend |
| 10 | Configures Gunicorn as a systemd service (auto-calculated worker count) |
| 11 | Configures Nginx as a reverse proxy for the API and static file server for React |
| 12 | Enables UFW firewall (SSH + HTTP + HTTPS), sets up daily backup cron, saves credentials |

After all steps, it runs verification checks on every service and reports pass/fail.

---

## Default Accounts

| Account | Email | Password |
|---------|-------|----------|
| Admin | `admin@colorformulation.local` | `ChangeMe123!` |
| Formulator | `formulator@colorformulation.local` | `ChangeMe123!` |

**Change these passwords immediately after first login.**

---

## File Locations

| Item | Path |
|------|------|
| Application | `/opt/colorformulation` |
| Backend config | `/opt/colorformulation/backend/.env` |
| Upload storage | `/var/lib/colorformulation/uploads` |
| Application log | `/var/log/colorformulation/app.log` |
| Access log | `/var/log/colorformulation/access.log` |
| Error log | `/var/log/colorformulation/error.log` |
| Backups | `/var/backups/colorformulation` |
| Credentials | `/root/.colorformulation_credentials` |

---

## Service Commands

```bash
systemctl status colorformulation       # Check app status
systemctl restart colorformulation      # Restart the app
systemctl stop colorformulation         # Stop the app
journalctl -u colorformulation -f       # Live application logs
systemctl status nginx                  # Check Nginx
systemctl status postgresql             # Check PostgreSQL
```

---

## Adding HTTPS (Optional)

If your server has a public domain name:

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d yourdomain.com
```

Certbot handles everything — certificate, Nginx config, and auto-renewal.

---

## Backups

The installer sets up a daily cron job at 2:00 AM that:
- Dumps the PostgreSQL database to a compressed file
- Archives all uploaded CXF files
- Cleans up backups older than 30 days

Manual backup:
```bash
bash /opt/colorformulation/scripts/backup.sh
```

Restore from backup:
```bash
# Database
gunzip -c /var/backups/colorformulation/db_TIMESTAMP.sql.gz | sudo -u postgres psql colorformulation

# Uploaded files
tar xzf /var/backups/colorformulation/uploads_TIMESTAMP.tar.gz -C /var/lib/colorformulation/
```

---

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
systemctl restart colorformulation
systemctl reload nginx
```

---

## Troubleshooting

### Gunicorn won't start

```bash
journalctl -u colorformulation -n 50 --no-pager
cat /var/log/colorformulation/error.log
```

### 502 Bad Gateway from Nginx

Gunicorn isn't running or isn't listening:
```bash
systemctl restart colorformulation
ss -tlnp | grep 5000   # Should show gunicorn
```

### Database connection errors

```bash
systemctl status postgresql
sudo -u postgres psql -d colorformulation -c "SELECT 1;"
cat /opt/colorformulation/backend/.env | grep DATABASE_URL
```

### Blank page / frontend not loading

```bash
ls /opt/colorformulation/frontend/build/index.html   # Must exist
# If missing, rebuild:
cd /opt/colorformulation/frontend && npm run build
systemctl reload nginx
```

### Permission errors

```bash
chown -R colorformulation:colorformulation /opt/colorformulation
chown -R colorformulation:colorformulation /var/lib/colorformulation
chown -R colorformulation:colorformulation /var/log/colorformulation
systemctl restart colorformulation
```

### Re-run the installer

The script is idempotent — you can safely run it again. It will update passwords,
rebuild everything, and restart services.
