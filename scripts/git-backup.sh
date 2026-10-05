#!/usr/bin/env bash
# 采集数据 git 备份：提交 data/、reports/ 变更并推送 origin
#
# 设计约定：
# - 推送失败不视为致命（数据已落盘本地，下个采集窗口自然重试），但最终失败
#   以 exit 4 退出，供 run-crawl.sh 把心跳降级为 down（不再静默断更）
# - 推送被拒（非快进）时先 fetch + rebase 把本地提交重放到远端之上再重试
#   （2026-10-06 加固：此前别处 checkout 直接推 GitHub 一次，本机 push 连续
#   两天静默失败，心跳照常 up、数据断更无人知）
# - 派生文件中的时间戳/元数据字段（generated_at/build_id/updated_at/mtime/
#   ai_elapsed_seconds/hash）每次采集都会刷新，仅这些行变化时不产生提交，
#   避免"每次运行都多一个空提交"；真实数据变化时会随本次一并提交
# - 连续多日无 auto 提交即为采集停摆的告警信号
#
# 用法: git-backup.sh "commit message"
# 退出码: 0 = 已推送或无可推内容；4 = 重试后仍未推送（数据已本地提交）
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
  # 远端领先（如别处 checkout 直接推了 GitHub）时，裸重试永远非快进被拒。
  # fetch 后确认远端不是 HEAD 的祖先，才 rebase（--autostash 容忍派生文件的
  # regen 噪声脏树）；rebase 失败则放弃重试，保持现场等人工处理。
  if git fetch origin 2>/dev/null \
      && git rev-parse --verify -q origin/main >/dev/null \
      && ! git merge-base --is-ancestor origin/main HEAD; then
    if git rebase --autostash origin/main; then
      log "rebased local commits onto origin/main, will retry push"
    else
      git rebase --abort 2>/dev/null || true
      log "ERROR: rebase onto origin/main failed (conflict?); stop retrying, needs manual handling"
      break
    fi
  fi
  [ "$i" -lt "$max_retry" ] && sleep $((i * 10))
done
log "ERROR: push failed after $max_retry attempts; data committed locally, next run will retry"
exit 4
