#!/usr/bin/env bash
set -euo pipefail

# ── System-level full backup: PostgreSQL + MinIO ──────────────────────────────
#
# Usage:
#   ./scripts/snapshot.sh              # 使用默认目录 ./snapshots/
#   ./scripts/snapshot.sh /mnt/backup  # 指定备份目录
#
# 依赖：Docker Compose（容器必须处于运行状态）
# 保留策略：最多 MAX_SNAPSHOTS 份（默认 30），自动轮转最旧的
#
# 产出结构：
#   snapshots/20260406_030000/
#   ├── database.dump        pg_dump custom 格式（支持 pg_restore 选择性恢复）
#   ├── minio-data.tar.gz    MinIO /data 目录完整打包
#   └── metadata.json        快照元信息
# ──────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

# ── Load .env ─────────────────────────────────────────────────────────────────

if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.env"
    set +a
fi

POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-homework}"
SNAPSHOT_BASE="${1:-${SNAPSHOT_DIR:-$PROJECT_ROOT/snapshots}}"
MAX_SNAPSHOTS="${MAX_SNAPSHOTS:-30}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
SNAPSHOT_PATH="$SNAPSHOT_BASE/$TIMESTAMP"

# ── Preflight checks ─────────────────────────────────────────────────────────

check_container() {
    if ! docker compose -f "$COMPOSE_FILE" ps --status running --format '{{.Name}}' 2>/dev/null | grep -q "$1"; then
        echo "ERROR: $1 container is not running" >&2
        exit 1
    fi
}

check_container postgres
check_container minio

mkdir -p "$SNAPSHOT_PATH"
echo "=== Snapshot: $TIMESTAMP ==="

# ── 1. PostgreSQL ─────────────────────────────────────────────────────────────

echo "[1/3] Backing up PostgreSQL..."
if docker compose -f "$COMPOSE_FILE" exec -T postgres \
    pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" --format=custom \
    > "$SNAPSHOT_PATH/database.dump"; then
    echo "      database.dump ($(du -h "$SNAPSHOT_PATH/database.dump" | cut -f1))"
else
    echo "ERROR: pg_dump failed" >&2
    rm -rf "$SNAPSHOT_PATH"
    exit 1
fi

# ── 2. MinIO ─────────────────────────────────────────────────────────────────

echo "[2/3] Backing up MinIO data..."
if docker compose -f "$COMPOSE_FILE" exec -T minio \
    tar -cf - -C /data . | gzip > "$SNAPSHOT_PATH/minio-data.tar.gz"; then
    echo "      minio-data.tar.gz ($(du -h "$SNAPSHOT_PATH/minio-data.tar.gz" | cut -f1))"
else
    echo "ERROR: MinIO backup failed" >&2
    rm -rf "$SNAPSHOT_PATH"
    exit 1
fi

# ── 3. Metadata ──────────────────────────────────────────────────────────────

echo "[3/3] Writing metadata..."
cat > "$SNAPSHOT_PATH/metadata.json" <<EOF
{
    "timestamp": "$TIMESTAMP",
    "created_at": "$(date -Iseconds)",
    "postgres_db": "$POSTGRES_DB",
    "postgres_user": "$POSTGRES_USER"
}
EOF

# ── Rotate ────────────────────────────────────────────────────────────────────

SNAPSHOT_COUNT=$(find "$SNAPSHOT_BASE" -mindepth 1 -maxdepth 1 -type d | wc -l)
if [[ "$SNAPSHOT_COUNT" -gt "$MAX_SNAPSHOTS" ]]; then
    EXCESS=$((SNAPSHOT_COUNT - MAX_SNAPSHOTS))
    echo "Rotating: removing $EXCESS oldest snapshot(s)..."
    find "$SNAPSHOT_BASE" -mindepth 1 -maxdepth 1 -type d | sort | head -n "$EXCESS" | xargs rm -rf
fi

echo "=== Done: $SNAPSHOT_PATH ==="
