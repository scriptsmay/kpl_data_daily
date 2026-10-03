# deploy/ — 部署产物与安装脚本

本目录承载「宿主机定时采集」方案的部署文件：采集、git 备份、同步触发均由宿主机直接
执行，消费方（cheer-service，Vercel）只读 GitHub raw，两侧职责分离。

```text
调度器（二选一，同一台机器只允许一种）
  ├─ kpl-cron-panel（推荐，web 面板可调频率）deploy/setup-panel.sh
  └─ systemd timer（固定频率）              deploy/setup-timer.sh
       └─ scripts/run-crawl.sh main|schedule
            ├─ python3 main.py            # 全量采集 -> data/
            │  或 python3 scripts/fetch-schedule.py   # 赛程 -> data/derived/{season}/schedule.json
            ├─ scripts/git-backup.sh      # 提交 data/、reports/ 变更并推送 origin（失败不阻断）
            ├─ 同步触发（读 .env 的 SYNC_TRIGGER_URL/SECRET）：
            │    GET /api/cron/daily（Bearer CRON_SECRET）通知 cheer-service
            │    立即读 GitHub raw 入库（幂等；失败不阻断，Vercel Cron 每日兜底）
            └─ uptime 心跳（仅 main，读 .env 的 UPTIME_PUSH_URL，未配置则跳过）

消费方（cheer-service on Vercel）: KPL_SOURCE=github，读 raw.githubusercontent.com
检测变更（ETag）后同步入库 Supabase，不依赖本机任何目录。
```

## 文件清单

| 文件 | 用途 |
| --- | --- |
| `panel/server.py` | kpl-cron-panel 调度面板（纯标准库；调度 + HTTP API + 单页 UI） |
| `panel/index.html` | 面板前端单页（改频率 / 立即执行 / 看状态与日志） |
| `panel/kpl-cron-panel.service` | 面板 systemd unit |
| `setup-panel.sh` | 幂等安装面板（含「旧 timer 未停用即拒绝安装」双调度防护） |
| `systemd/kpl-data-daily.service` | 全量采集 oneshot 服务（main.py） |
| `systemd/kpl-data-daily.timer` | 每日 03:00 触发，Persistent=true 补偿停机错过窗口 |
| `systemd/kpl-data-schedule.service` | 赛程采集 oneshot 服务（fetch-schedule.py） |
| `systemd/kpl-data-schedule.timer` | 每 6 小时整点触发 |
| `setup-timer.sh` | 幂等安装 timer（固定频率路线，与面板互斥） |

配套脚本在 `scripts/run-crawl.sh`（采集入口）与 `scripts/git-backup.sh`（数据备份）。

## 调度面板（kpl-cron-panel）

```bash
# 前提：仓库位于 /root/kpl-data-daily，root 身份；本机未启用 kpl-data-*.timer
sudo bash deploy/setup-panel.sh
```

- 监听 `127.0.0.1:8899`（`PANEL_BIND`/`PANEL_PORT` 可覆盖），公网经反代暴露；**登录与会话由面板自身管理**——
  未认证访问出登录表单页，`POST /login` 校验 `.panel-password`（600，不入库）成功后种 `kpl_session`
  会话 cookie（HMAC 签名 + 7 天，HttpOnly SameSite=Lax）。不使用浏览器原生 basic auth 弹窗
  （WebView/移动端不渲染该弹窗，实测表现为 401 空白页）；
- **API 鉴权**：**会话 cookie 为主通道**（登录后浏览器自动携带，覆盖页面内所有 fetch）；`.panel-token`
  （600，不入库）仍作为命令行通道被接受——`curl -H "X-Panel-Token: $(cat /root/kpl-data-daily/.panel-token)"
  http://127.0.0.1:8899/api/status`。token 同时充当会话 cookie 的 HMAC 签名密钥。设计背景：曾用
  反代 basicauth，实测浏览器 fetch 不携带缓存的基本认证（401），且原生弹窗在 WebView 不渲染，遂整体
  改为面板内建表单登录；
- 频率配置落 `/root/kpl-data-daily/.panel-config.json`（不入库）；interval 最小 **1 小时**
  （服务端硬校验，频率红线），1~24 小时或 daily `HH:MM` 两种模式；
- 运行日志落 `logs/panel/<job>/*.log`（保留 60 份），运行历史 `logs/panel/history.json`；
- **全局串行**：同一时刻最多一个采集（两个 job 共享 git 工作区，并发会撞 index.lock），
  撞点时后到者顺延到下个轮询（15s）；
- 面板重启/停机期间的窗口**不补跑**（锚点式墙钟重排，错过即错过；需要时面板里「立即执行」）。

## 安装（systemd timer 路线）

```bash
# 前提：仓库位于 /root/kpl-data-daily，root 身份，系统 python3 已装 requests
sudo bash deploy/setup-timer.sh

# 首跑验证
systemctl start kpl-data-daily.service
journalctl -u kpl-data-daily.service -n 50 --no-pager
```

## 运维速查

| 场景 | 命令 |
| --- | --- |
| 手动补跑全量采集 | `systemctl start kpl-data-daily.service` |
| 手动补跑赛程采集 | `systemctl start kpl-data-schedule.service` |
| 查看日志 | `journalctl -u kpl-data-daily.service -n 100 --no-pager` |
| 修改频率 | 编辑对应 `.timer` 的 `OnCalendar` -> `systemctl daemon-reload && systemctl restart <timer>` |
| 停用 | `systemctl disable --now kpl-data-daily.timer kpl-data-schedule.timer` |

## 注意事项

- **单元文件路径写死为 `/root/kpl-data-daily`**：仓库不在该位置时 `setup-timer.sh` /
  `setup-panel.sh` 会拒绝安装，需先迁移目录或同步修改 unit 内的路径。
- **同一台机器只允许一种调度器**：面板与 timer 并存会重复采集、互相踩 git 工作区；
  `setup-panel.sh` 检测到本机 timer 在跑会拒绝安装。
- **代码变更走仓库**：直接改宿主机目录下的 `.py` / 脚本会被下一次代码同步覆盖；
  unit 文件同理，改动应提交进 `deploy/` 后重新执行安装脚本。
- **拉新代码前先清工作区**：git 备份跳过的时间戳漂移会以未暂存改动留在 `data/`
  （属预期），`git merge --ff-only` 若被其挡住，先 `git checkout -- data reports`
  或 `git stash` 恢复干净再合并。
- **频率红线**：调整频率前评估宿主机资源与上游 API 限流，最小 1 小时（面板服务端已硬校验）。
- **git 备份容错**：推送失败只告警不阻断采集；连续多日无 `auto:` 提交即为停摆信号。
- **同步触发（推荐配置）**：`.env` 配 `SYNC_TRIGGER_URL`（如
  `https://api-vercel.kplwuyan.site/api/cron/daily`）与 `SYNC_TRIGGER_SECRET`
  （与 cheer-service Vercel 侧 `CRON_SECRET` 同值）后，每次采集完成即触发消费方入库；
  未配置时退化为 Vercel Cron 每日一次同步。
- **心跳（可选）**：在仓库根目录 `.env` 配置 `UPTIME_PUSH_URL` 后，每日采集结束会上报
  up/down；仅 main 采集发心跳，避免高频任务掩盖主链路停摆。
- **迁移机器**：新机器 clone 本仓库到 `/root/kpl-data-daily`，装好 python3 + requests /
  python-dotenv / openai 与 git 推送凭证，补 `.env`（OPENAI_*、UPTIME_PUSH_URL、
  SYNC_TRIGGER_*），重跑 `deploy/setup-panel.sh` 即可恢复链路。
