#!/usr/bin/env bash
# 安装 kpl-cron-panel 调度面板（幂等，可重复执行）
#
# 前提:
# - 本仓库位于 /root/kpl-data-daily（unit 内路径按此写死）
# - 以 root 执行；系统 python3（纯标准库，无 pip 依赖）
# - 本机不再启用 kpl-data-*.timer（面板是唯一调度器，双调度会重复采集）
#
# 执行内容: 校验环境 -> 安装 unit -> 建日志目录/默认配置 -> daemon-reload
#           -> enable --now -> 打印面板地址
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_SRC="$REPO_ROOT/deploy/panel/kpl-cron-panel.service"
UNIT_DST="/etc/systemd/system/kpl-cron-panel.service"
EXPECTED_DIR="/root/kpl-data-daily"
PANEL_PORT="${PANEL_PORT:-8899}"

log() { echo "[setup-panel $(date '+%Y-%m-%d %H:%M:%S')] $*"; }

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: run as root" >&2; exit 1
fi
if [ "$REPO_ROOT" != "$EXPECTED_DIR" ]; then
  echo "ERROR: repo is at $REPO_ROOT but unit expects $EXPECTED_DIR" >&2; exit 1
fi

# 双调度防护：宿主机若还在跑旧 timer，先停用再装面板
if systemctl list-unit-files 2>/dev/null | grep -qE '^kpl-data-(daily|schedule)\.timer'; then
  if systemctl is-active --quiet kpl-data-daily.timer || systemctl is-active --quiet kpl-data-schedule.timer; then
    log "detected active kpl-data-*.timer on this host — disable them first (double scheduling)"
    echo "  systemctl disable --now kpl-data-daily.timer kpl-data-schedule.timer" >&2
    exit 1
  fi
fi

python3 --version
# 端口冲突只挡「面板未在跑」的场景；面板本身在跑时端口被自己占用属正常（重跑=更新重启）
if ! systemctl is-active --quiet kpl-cron-panel.service; then
  ss -tln | grep -q ":${PANEL_PORT} " && { echo "ERROR: port ${PANEL_PORT} already in use" >&2; exit 1; } || true
fi

install -m 644 "$UNIT_SRC" "$UNIT_DST"

# 日志目录、默认配置与 API token（已存在则不动）
mkdir -p "$REPO_ROOT/logs/panel/main" "$REPO_ROOT/logs/panel/schedule"
if [ ! -f "$REPO_ROOT/.panel-token" ]; then
  (openssl rand -hex 24 2>/dev/null || od -An -N24 -tx1 /dev/urandom | tr -d ' \n') > "$REPO_ROOT/.panel-token"
  chmod 600 "$REPO_ROOT/.panel-token"
  log "generated .panel-token (API 鉴权用，勿提交；curl 调 API 加 -H \"X-Panel-Token: \$(cat $REPO_ROOT/.panel-token)\")"
fi
if [ ! -f "$REPO_ROOT/.panel-password" ]; then
  (openssl rand -base64 18 2>/dev/null | tr -d '/+=') > "$REPO_ROOT/.panel-password"
  chmod 600 "$REPO_ROOT/.panel-password"
  log "generated .panel-password (登录表单密码，勿提交)"
fi
if [ ! -f "$REPO_ROOT/.panel-config.json" ]; then
  cat > "$REPO_ROOT/.panel-config.json" <<'EOF'
{
  "jobs": {
    "main": { "enabled": true, "mode": "interval", "interval_hours": 1, "minute": 0, "daily_at": "03:00" },
    "schedule": { "enabled": true, "mode": "interval", "interval_hours": 6, "minute": 0, "daily_at": "06:00" }
  }
}
EOF
  log "wrote default .panel-config.json (main: 每 1 小时 / schedule: 每 6 小时)"
fi

systemd-analyze verify "$UNIT_DST"
systemctl daemon-reload
systemctl enable kpl-cron-panel.service
systemctl restart kpl-cron-panel.service
sleep 1
systemctl --no-pager status kpl-cron-panel.service | head -8

log "panel ready: http://127.0.0.1:${PANEL_PORT}  (公网经反代 + basic auth 暴露)"
log "日志目录: ${REPO_ROOT}/logs/panel/<job>/ ；面板自身日志: journalctl -u kpl-cron-panel.service"
