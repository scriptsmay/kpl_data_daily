#!/usr/bin/env bash
# 采集数据 git 备份：提交 data/、reports/ 变更并推送 origin
#
# 设计约定：
# - 推送失败不视为致命（数据已落盘本地，下个采集窗口自然重试），恒定 exit 0
# - 派生文件中的时间戳/元数据字段（generated_at/build_id/updated_at/mtime/
#   ai_elapsed_seconds/hash）每次采集都会刷新，仅这些行变化时不产生提交，
#   避免"每次运行都多一个空提交"；真实数据变化时会随本次一并提交
# - 连续多日无 auto 提交即为采集停摆的告警信号
#
# 用法: git-backup.sh "commit message"
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
MSG="${1:-auto: data backup $(date +%Y%m%d-%H%M)}"

log() { echo "[git-backup $(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# 提交身份兜底（systemd 环境通常没有全局 git config）
git config user.name >/dev/null 2>&1 || git config user.name "Server Cron"
git config user.email >/dev/null 2>&1 || git config user.email "actions@github.com"

if ! git remote get-url origin >/dev/null 2>&1; then
  log "no origin remote configured, skip backup"
  exit 0
fi

git add -A -- data reports

# git diff -I 忽略"仅命中这些模式"的行级变更；全部变更可忽略则无实质更新
if git diff --cached --quiet \
    -I '"generated_at"' -I '"build_id"' -I '"updated_at"' \
    -I '"mtime"' -I '"ai_elapsed_seconds"' -I '"hash"'; then
  log "no real data changes, skip commit"
  git reset -q -- data reports 2>/dev/null || true
  exit 0
fi

if ! git commit -m "$MSG"; then
  log "git commit failed (worktree may be locked), skip push"
  exit 0
fi
log "committed: $MSG"

max_retry=3
for i in $(seq 1 "$max_retry"); do
  if git push origin HEAD; then
    log "push OK (attempt $i/$max_retry)"
    exit 0
  fi
  log "push attempt $i/$max_retry failed"
  [ "$i" -lt "$max_retry" ] && sleep $((i * 10))
done
log "WARNING: push failed after $max_retry attempts; data saved locally, will retry next run"
exit 0
