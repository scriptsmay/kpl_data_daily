#!/usr/bin/env bash
# 在宿主机安装 kpl-data-daily 的 systemd timer（幂等，可重复执行）
#
# 前提:
# - 本仓库位于 /root/kpl-data-daily（deploy/systemd/*.service 内的路径按此写死）
# - 以 root 执行；系统 python3 已安装 requests
#
# 执行内容: 安装 4 个 unit 文件 -> systemd-analyze verify -> daemon-reload
#           -> enable --now 两个 timer -> 打印下次触发时间
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_SRC="$REPO_ROOT/deploy/systemd"
UNIT_DST="/etc/systemd/system"
EXPECTED_DIR="/root/kpl-data-daily"

log() { echo "[setup-timer $(date '+%Y-%m-%d %H:%M:%S')] $*"; }

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: run as root" >&2
  exit 1
fi

if [ ! -f "$REPO_ROOT/main.py" ]; then
  echo "ERROR: main.py not found in $REPO_ROOT" >&2
  exit 1
fi

if [ "$REPO_ROOT" != "$EXPECTED_DIR" ]; then
  echo "ERROR: repo is at $REPO_ROOT but unit files expect $EXPECTED_DIR" >&2
  echo "       relocate the repo, or adjust WorkingDirectory/ExecStart in deploy/systemd/*.service" >&2
  exit 1
fi

python3 --version
python3 -c "import requests" || { echo "ERROR: python3 requests missing" >&2; exit 1; }

install -m 644 "$UNIT_SRC/kpl-data-daily.service" "$UNIT_DST/"
install -m 644 "$UNIT_SRC/kpl-data-daily.timer" "$UNIT_DST/"
install -m 644 "$UNIT_SRC/kpl-data-schedule.service" "$UNIT_DST/"
install -m 644 "$UNIT_SRC/kpl-data-schedule.timer" "$UNIT_DST/"

log "verifying unit files"
systemd-analyze verify "$UNIT_DST/kpl-data-daily.service" "$UNIT_DST/kpl-data-schedule.service"

systemctl daemon-reload
systemctl enable --now kpl-data-daily.timer kpl-data-schedule.timer

log "installed. current timers:"
systemctl list-timers --all | grep -E 'kpl-data|NEXT' || true
log "manual first run: systemctl start kpl-data-daily.service && journalctl -u kpl-data-daily.service -n 50"
