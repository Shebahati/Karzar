# VPS storage housekeeping

Operator runbook for automated disk hygiene on the Karzar live VPS (`srv5944957438`, `CR-011`).

## Background

Repeated on-VPS Docker image builds (GitHub Actions self-hosted runner) accumulated roughly **62GB** of BuildKit cache under `/var/lib/containerd` by September 2026. A controlled manual `docker builder prune -a -f` on **2026-09-15** reclaimed **61.71GB** (filesystem used dropped ~75G → ~20G) without touching application images, volumes, or backups.

This subsystem automates **age-filtered unused BuildKit cache** cleanup and **tiered local backup retention**. It does **not** manage Docker images, containers, networks, or volumes.

## Components

| Artifact | Purpose |
|----------|---------|
| `scripts/ops/vps_storage_housekeeping.sh` | Main entry (default **dry-run**) |
| `scripts/ops/vps_storage_housekeeping_lib.sh` | Host/build gates, disk stats, safety checks |
| `scripts/ops/backup_retention.py` | Deterministic retention planning |
| `deploy/systemd/karzar-storage-housekeeping.service` | Oneshot apply unit (template) |
| `deploy/systemd/karzar-storage-housekeeping.timer` | Weekly schedule (template) |

Existing backup **creation** remains `scripts/backup_db.sh`, `scripts/backup_uploads.sh`, and `deploy/staging/scripts/install-backup-cron.sh` — this subsystem only **retains** files already in `backups/`.

## Safety gates

1. **Host identity** — expected hostname, `KARZAR_ROOT`, `lathe_api` + `lathe_postgres` running.
2. **Lock** — `flock` on `/run/lock/karzar-storage-housekeeping.lock`.
3. **Active build/deploy** — skips prune and retention delete if `Runner.Worker`, `docker build`, `buildctl`, or deploy scripts are active. Idle `Runner.Listener` is allowed.
4. **BuildKit** — only `docker builder prune -a -f --filter until=168h` (configurable). Preflight checks Docker help text for `until`/`duration` filter semantics; **no** unrestricted prune fallback. If Docker rejects the filter at apply time, the run **fails closed**.
5. **Backup safety** — before any delete under `--apply`: latest **canonical** DB backup (`karzar_YYYYMMDD_HHMMSS.sql.gz`) chosen by **filename UTC timestamp** (not filesystem `mtime`); must be &lt; 36h old by that timestamp, `gzip -t` OK, size &gt; 0, ≥2 valid canonical DB backups. Unknown/baseline names do not satisfy the freshness gate.

## Disk thresholds (reporting only)

| State | Usage |
|-------|-------|
| NORMAL | &lt; 50% |
| WARNING | ≥ 65% (`KARZAR_DISK_WARNING_PERCENT`) |
| CRITICAL | ≥ 80% (`KARZAR_DISK_CRITICAL_PERCENT`) |

Critical disk does **not** trigger aggressive image deletion — only the same age-filtered BuildKit policy. If still critical, the script sets `MANUAL_OPERATOR_INTERVENTION_REQUIRED=YES`.

## BuildKit policy

- **Schedule (when timer installed):** Sunday 04:30 local, `RandomizedDelaySec=30m`
- **Retention:** unused cache older than **7 days** (`KARZAR_BUILDKIT_CACHE_UNTIL_HOURS=168`)

## Backup retention

**Database** (`karzar_YYYYMMDD_HHMMSS.sql.gz`):

- Keep newest **14** calendar days (newest file per day)
- Keep **8** weekly slots (newest file per ISO week)
- Keep **12** monthly slots (newest file per month)
- Union of slots → keep; others → delete candidate (only under `--apply` + safety gate)

**Uploads** (`karzar_uploads_YYYYMMDD_HHMMSS.tar.gz`):

- **8** weekly + **12** monthly (same slot rules)

Non-canonical names (e.g. `karzar_prod_baseline_*.sql.gz`) → **KEEP_UNKNOWN** (never auto-deleted).

## Usage

```bash
cd /opt/karzar/Karzar

# Default: dry-run
sudo bash scripts/ops/vps_storage_housekeeping.sh

# Explicit dry-run + verbose
sudo bash scripts/ops/vps_storage_housekeeping.sh --dry-run --verbose

# Apply (owner authorization required)
sudo bash scripts/ops/vps_storage_housekeeping.sh --apply
```

Machine-readable summary lines are printed at exit (`KARZAR_HOUSEKEEPING_RESULT=`, etc.).

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success, dry-run complete, or lock busy (no work) |
| 10 | Host identity gate failed |
| 11 | BuildKit `--filter until=` unsupported (`--apply` only) |
| 12 | BuildKit prune failed |
| 13 | Retention delete failed |
| 2 | Invalid CLI arguments |

## Installation (not automatic)

```bash
sudo cp deploy/systemd/karzar-storage-housekeeping.service /etc/systemd/system/
sudo cp deploy/systemd/karzar-storage-housekeeping.timer /etc/systemd/system/
sudo systemctl daemon-reload
# Owner activation only (enable the TIMER, not the oneshot service):
# sudo systemctl enable --now karzar-storage-housekeeping.timer
```

**Schedule:** `OnCalendar=Sun *-*-* 04:30:00` uses the **server local timezone** (`timedatectl`). On the production VPS (UTC), this is **04:30 UTC Sunday**, after daily backup cron (03:15 DB / 03:30 uploads UTC).

Optional file logrotate template: `deploy/systemd/karzar-storage-housekeeping.logrotate`.

## Disable / rollback

```bash
sudo systemctl disable --now karzar-storage-housekeeping.timer
sudo rm -f /etc/systemd/system/karzar-storage-housekeeping.{service,timer}
sudo systemctl daemon-reload
```

## Logs

```bash
journalctl -u karzar-storage-housekeeping.service -n 200 --no-pager
```

## Forbidden commands

This subsystem must **never** invoke:

- `docker system prune`
- `docker image prune`
- `docker volume prune`
- `docker container prune`

## Emergency full disk

1. Run housekeeping **dry-run** and review retention table.
2. If BuildKit is the driver, owner may run the same age-filtered prune manually after confirming no active build.
3. Do **not** delete rollback images (`rollback-*`), staging tags, Postgres/upload volumes, or backups without explicit owner policy.
4. Off-host backup sync remains mandatory for DR (`scripts/backup_offsite_sync.sh`).
