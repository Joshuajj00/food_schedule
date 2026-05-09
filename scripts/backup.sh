#!/usr/bin/env bash
# 일일 백업 스크립트.
# crontab 등록: 0 2 * * * /path/to/food_schedule/scripts/backup.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
HOST="${HOST:-localhost:1414}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

mkdir -p "$BACKUP_DIR"

DATE=$(date +%Y%m%d_%H%M%S)
OUTFILE="$BACKUP_DIR/diet_backup_$DATE.json"

echo "[$(date)] 백업 시작 → $OUTFILE"

if curl -sf "http://$HOST/api/backup/export" -o "$OUTFILE.tmp"; then
    mv "$OUTFILE.tmp" "$OUTFILE"
    SIZE=$(stat -c%s "$OUTFILE" 2>/dev/null || stat -f%z "$OUTFILE")
    echo "[$(date)] 백업 완료: ${SIZE}바이트"
else
    rm -f "$OUTFILE.tmp"
    echo "[$(date)] 백업 실패: API 호출 오류" >&2
    exit 1
fi

find "$BACKUP_DIR" -name 'diet_backup_*.json' -mtime +"$RETENTION_DAYS" -delete
echo "[$(date)] ${RETENTION_DAYS}일 이상 된 백업 정리 완료"
