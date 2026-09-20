#!/usr/bin/env bash
# KPL 数据采集统一入口（宿主机 systemd timer 调用，也可手动执行）
#
# 用法: run-crawl.sh main|schedule
#   main     - 全量采集（python3 main.py），每日一次
#   schedule - 赛程采集（python3 scripts/fetch-schedule.py），每 6 小时一次
#
# 流程: 执行爬虫 -> git 备份（失败不阻断）-> uptime 心跳（仅 main）
# 退出码 = 爬虫退出码；备份/心跳失败不影响 systemd 对本次采集成败的判定
set -uo pipefail

MODE="${1:-main}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

log() { echo "[run-crawl $(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# 从 .env 读取单个变量值（python-dotenv 格式，容忍引号；文件不存在返回空串）
env_value() {
  local key="$1" val=""
  if [ -f "$REPO_ROOT/.env" ]; then
    val="$(grep -E "^${key}=" "$REPO_ROOT/.env" | tail -n 1 | cut -d= -f2- \
      | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' \
            -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")"
  fi
  printf '%s' "$val"
}

ok=1
case "$MODE" in
  main)
    log "start main crawl: python3 main.py"
    python3 main.py
    rc=$?
    [ "$rc" -ne 0 ] && ok=0
    log "main.py exited $rc"
    msg="auto: daily crawl $(date +%Y%m%d)"
    ;;
  schedule)
    log "start schedule crawl: python3 scripts/fetch-schedule.py"
    python3 scripts/fetch-schedule.py
    rc=$?
    [ "$rc" -ne 0 ] && ok=0
    log "fetch-schedule.py exited $rc"
    msg="auto: schedule crawl $(date +%Y%m%d-%H%M)"
    ;;
  *)
    echo "usage: $0 main|schedule" >&2
    exit 2
    ;;
esac

bash "$REPO_ROOT/scripts/git-backup.sh" "$msg" || log "git backup failed (non-fatal)"

# 心跳只挂每日主采集：schedule 每 6 小时一次，若也发心跳会掩盖 main 停摆
if [ "$MODE" = "main" ]; then
  url="$(env_value UPTIME_PUSH_URL)"
  if [ -n "$url" ]; then
    # .env 里的 URL 可能被配成自带 query（如 ?status=up&msg=OK）：直接追加会产生
    # 重复参数，kuma 把重复 status 解析成数组后按非 up 判 Down、甚至 404。
    # 统一截掉旧 query，用标准参数重建（2026-09-20 告警根因）。
    base="${url%%\?*}"
    if [ "$ok" -eq 1 ]; then
      qs="status=up&msg=OK"
    else
      qs="status=down&msg=crawl%20failed"
    fi
    sent=0
    for i in 1 2 3; do
      if curl -fsS --max-time 10 "${base}?${qs}" >/dev/null 2>&1; then
        log "heartbeat sent ($qs, attempt $i/3)"
        sent=1
        break
      fi
      [ "$i" -lt 3 ] && sleep 10
    done
    [ "$sent" -eq 0 ] && log "WARNING: heartbeat failed after 3 attempts"
  else
    log "UPTIME_PUSH_URL not set in .env, heartbeat skipped"
  fi
fi

exit "$rc"
