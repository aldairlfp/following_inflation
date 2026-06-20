#!/bin/sh

DB_SOURCE="/data/exchange_rates.db"
BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/exchange_rates_$TIMESTAMP.db"
KEEP_LAST=14  # keep last 14 backups (7 days × 2/day)

# Only backup if the source DB exists
if [ ! -f "$DB_SOURCE" ]; then
  echo "[$TIMESTAMP] Source DB not found, skipping."
  exit 0
fi

# Safe hot backup using sqlite3
sqlite3 "$DB_SOURCE" ".backup '$BACKUP_FILE'"

echo "[$TIMESTAMP] Backup saved to $BACKUP_FILE"

# Remove old backups, keep only the last $KEEP_LAST
ls -t "$BACKUP_DIR"/exchange_rates_*.db 2>/dev/null | tail -n +$((KEEP_LAST + 1)) | xargs -r rm --
echo "[$TIMESTAMP] Cleanup done, keeping last $KEEP_LAST backups."
