# deploy/ — 部署产物与安装脚本

本目录承载「宿主机 systemd timer 定时采集」方案的部署文件：采集、git 备份均由宿主机直
接执行，消费方（API 容器）只读挂载本仓库数据目录，两侧职责分离。

```text
systemd timer (03:00 每日 / 00/6 每 6 小时)
  └─ scripts/run-crawl.sh main|schedule
       ├─ python3 main.py            # 全量采集 -> data/
       │  或 python3 scripts/fetch-schedule.py   # 赛程 -> data/derived/{season}/schedule.json
       ├─ scripts/git-backup.sh      # 提交 data/、reports/ 变更并推送 origin（失败不阻断）
       └─ uptime 心跳（仅 main，读 .env 的 UPTIME_PUSH_URL，未配置则跳过）

消费方（API 容器）: 只读挂载本仓库目录，基于文件 mtime 检测变更后同步自身存储，
不执行任何 git / 爬虫操作。
```

## 文件清单

| 文件 | 用途 |
|---|---|
| `systemd/kpl-data-daily.service` | 全量采集 oneshot 服务（main.py） |
| `systemd/kpl-data-daily.timer` | 每日 03:00 触发，Persistent=true 补偿停机错过窗口 |
| `systemd/kpl-data-schedule.service` | 赛程采集 oneshot 服务（fetch-schedule.py） |
| `systemd/kpl-data-schedule.timer` | 每 6 小时整点触发 |
| `setup-timer.sh` | 幂等安装：拷贝 unit -> verify -> daemon-reload -> enable --now |

配套脚本在 `scripts/run-crawl.sh`（采集入口）与 `scripts/git-backup.sh`（数据备份）。

## 安装

```bash
# 前提：仓库位于 /root/kpl-data-daily，root 身份，系统 python3 已装 requests
sudo bash deploy/setup-timer.sh

# 首跑验证
systemctl start kpl-data-daily.service
journalctl -u kpl-data-daily.service -n 50 --no-pager
```

## 运维速查

| 场景 | 命令 |
|---|---|
| 手动补跑全量采集 | `systemctl start kpl-data-daily.service` |
| 手动补跑赛程采集 | `systemctl start kpl-data-schedule.service` |
| 查看日志 | `journalctl -u kpl-data-daily.service -n 100 --no-pager` |
| 修改频率 | 编辑对应 `.timer` 的 `OnCalendar` -> `systemctl daemon-reload && systemctl restart <timer>` |
| 停用 | `systemctl disable --now kpl-data-daily.timer kpl-data-schedule.timer` |

## 注意事项

- **单元文件路径写死为 `/root/kpl-data-daily`**：仓库不在该位置时 `setup-timer.sh` 会拒绝
  安装，需先迁移目录或同步修改 unit 内的 `WorkingDirectory` / `ExecStart`。
- **代码变更走仓库**：直接改宿主机目录下的 `.py` / 脚本会被下一次代码同步覆盖；
  unit 文件同理，改动应提交进 `deploy/systemd/` 后重新执行安装脚本。
- **拉新代码前先清工作区**：git 备份跳过的时间戳漂移会以未暂存改动留在 `data/`
  （属预期），`git merge --ff-only` 若被其挡住，先 `git checkout -- data reports`
  或 `git stash` 恢复干净再合并。
- **频率红线**：调整 `OnCalendar` 前评估宿主机资源与上游 API 限流，禁止加密到小时级以上。
- **git 备份容错**：推送失败只告警不阻断采集；连续多日无 `auto:` 提交即为停摆信号。
- **心跳（可选）**：在仓库根目录 `.env` 配置 `UPTIME_PUSH_URL` 后，每日采集结束会上报
  up/down；仅 main 采集发心跳，避免高频任务掩盖主链路停摆。
- **迁移机器**：新机器 clone 本仓库到 `/root/kpl-data-daily`，装好 python3 + requests 与
  git 推送凭证，重跑 `deploy/setup-timer.sh` 即可恢复链路。
