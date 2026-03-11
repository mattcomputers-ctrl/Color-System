#!/usr/bin/env bash
# =============================================================================
# Color Formulation System — Backup Script
# =============================================================================
# Creates a timestamped backup of the database and uploaded files.
#
# Usage:
#   sudo bash scripts/backup.sh [backup_dir]
#
# Default backup directory: /var/backups/colorformulation
# =============================================================================

set -euo pipefail

BACKUP_DIR="${1:-/var/backups/colorformulation}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="colorformulation"
UPLOAD_DIR="/var/lib/colorformulation/uploads"

mkdir -p "$BACKUP_DIR"

echo "Backing up Color Formulation System..."

# Database dump
echo "  Dumping database..."
sudo -u postgres pg_dump "$DB_NAME" | gzip > "$BACKUP_DIR/db_${TIMESTAMP}.sql.gz"

# Upload files
echo "  Backing up uploaded files..."
if [ -d "$UPLOAD_DIR" ]; then
    tar czf "$BACKUP_DIR/uploads_${TIMESTAMP}.tar.gz" -C "$(dirname "$UPLOAD_DIR")" "$(basename "$UPLOAD_DIR")"
fi

# Clean up old backups (keep last 30 days)
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete

echo "Backup complete:"
ls -lh "$BACKUP_DIR"/*_${TIMESTAMP}.*
