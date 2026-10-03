#!/usr/bin/env python3
"""kpl-cron-panel — KPL 数据采集调度面板（纯标准库，无第三方依赖）

取代宿主机 systemd timer 成为采集链路的唯一调度器：
- 按 .panel-config.json 的频率调度 scripts/run-crawl.sh main|schedule（保留
  git 备份、同步触发、心跳等既有环节）
- HTTP API + 单页 UI：改频率、立即执行、看状态与日志；默认只监听 127.0.0.1，
  公网访问经反代（Caddy basic auth）
- 全局互斥：同一时刻最多一个采集在跑——两个 job 的 git 提交共享同一工作区，
  并发会撞 index.lock；撞点时后到者在下个轮询补跑

频率红线：interval 最小 1 小时、最大 24 小时（更长的周期用 daily 模式表达），
服务端硬校验，与 SOP「禁止加密到小时级以上」一致。

时区：使用系统本地时区（宿主机应为 Asia/Shanghai），daily_at / next_run 均为本地时间。
"""

import hmac
import json
import os
import re
import shutil
import signal
import socketserver
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler

REPO_ROOT = os.environ.get(
    "KPL_PANEL_REPO_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")),
)
CONFIG_PATH = os.path.join(REPO_ROOT, ".panel-config.json")
TOKEN_PATH = os.path.join(REPO_ROOT, ".panel-token")
PASSWORD_PATH = os.path.join(REPO_ROOT, ".panel-password")
LOG_ROOT = os.path.join(REPO_ROOT, "logs", "panel")
HISTORY_PATH = os.path.join(LOG_ROOT, "history.json")
INDEX_HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

BIND = os.environ.get("PANEL_BIND", "127.0.0.1")
PORT = int(os.environ.get("PANEL_PORT", "8899"))

POLL_SECONDS = 15          # 调度轮询间隔
RUN_TIMEOUT_SECONDS = 2 * 3600   # 单次采集兜底超时（正常 3 分钟量级）
LOG_KEEP = 60              # 每 job 保留的日志文件数
HISTORY_KEEP = 300         # 保留的运行历史条数
LOG_TAIL_BYTES = 8000      # log 接口返回的尾部字节数

JOBS = ("main", "schedule")

DEFAULT_CONFIG = {
    "jobs": {
        "main": {"enabled": True, "mode": "interval", "interval_hours": 1, "minute": 0, "daily_at": "03:00"},
        "schedule": {"enabled": True, "mode": "interval", "interval_hours": 6, "minute": 0, "daily_at": "06:00"},
    }
}


def log(msg):
    print(f"[panel {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------- 配置

_config_lock = threading.Lock()


def _validate_job_cfg(name, cfg):
    if not isinstance(cfg, dict):
        raise ValueError("配置须为对象")
    out = {
        "enabled": bool(cfg.get("enabled", True)),
        "mode": cfg.get("mode", "interval"),
        "interval_hours": cfg.get("interval_hours", 1),
        "minute": cfg.get("minute", 0),
        "daily_at": cfg.get("daily_at", "03:00"),
    }
    if out["mode"] not in ("interval", "daily"):
        raise ValueError("mode 仅支持 interval | daily")
    if out["mode"] == "interval":
        try:
            ih = int(out["interval_hours"])
            mi = int(out["minute"])
        except (TypeError, ValueError):
            raise ValueError("interval_hours / minute 须为整数")
        if not 1 <= ih <= 24:
            raise ValueError("interval_hours 须在 1~24 之间（频率红线：最小 1 小时；更长周期用 daily 模式）")
        if not 0 <= mi <= 59:
            raise ValueError("minute 须在 0~59 之间")
        out["interval_hours"] = ih
        out["minute"] = mi
    else:
        m = re.fullmatch(r"\d{2}:\d{2}", str(out["daily_at"] or ""))
        if not m:
            raise ValueError("daily_at 格式须为 HH:MM")
        hh, mm = int(out["daily_at"][:2]), int(out["daily_at"][3:5])
        if hh > 23 or mm > 59:
            raise ValueError("daily_at 时间非法")
    return out


def load_config():
    with _config_lock:
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except FileNotFoundError:
            cfg = json.loads(json.dumps(DEFAULT_CONFIG))
            save_config(cfg)
        except Exception as e:  # 损坏时兜底为默认并保留现场
            log(f"ERROR: config load failed ({e}), fallback to default (broken file kept as .panel-config.json.broken)")
            shutil.move(CONFIG_PATH, CONFIG_PATH + ".broken")
            cfg = json.loads(json.dumps(DEFAULT_CONFIG))
            save_config(cfg)
        jobs = {}
        for name in JOBS:
            raw = (cfg.get("jobs") or {}).get(name) or {}
            try:
                jobs[name] = _validate_job_cfg(name, raw)
            except ValueError as e:
                log(f"WARNING: job {name} config invalid ({e}), using default")
                jobs[name] = dict(DEFAULT_CONFIG["jobs"][name])
        return {"jobs": jobs}


def save_config(cfg):
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, CONFIG_PATH)


# ---------------------------------------------------------------- 调度

def compute_next_run(job_cfg, now=None):
    """按锚点式墙钟计算下次触发：interval = 小时数整倍数对齐，daily = 固定时刻。"""
    now = now or datetime.now()
    if not job_cfg.get("enabled"):
        return None
    if job_cfg["mode"] == "daily":
        hh, mm = int(job_cfg["daily_at"][:2]), int(job_cfg["daily_at"][3:5])
        cand = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if cand <= now:
            cand += timedelta(days=1)
        return cand
    ih, mi = job_cfg["interval_hours"], job_cfg["minute"]
    cand = now.replace(minute=mi, second=0, microsecond=0)
    for _ in range(48):
        if cand > now and cand.hour % ih == 0:
            return cand
        cand += timedelta(hours=1)
    return None  # 理论不可达


class JobState:
    def __init__(self, name):
        self.name = name
        self.cfg = {}
        self.next_run = None
        self.running = None  # dict: {started_at, trigger, log_file} 或 None
        self.proc = None

    def status(self):
        hist = read_history(self.name)
        return {
            "config": self.cfg,
            "next_run": self.next_run.isoformat(timespec="seconds") if self.next_run else None,
            "running": dict(self.running) if self.running else None,
            "last": hist[0] if hist else None,
            "recent": hist[:10],
        }


_states = {name: JobState(name) for name in JOBS}
_run_lock = threading.Lock()  # 全局互斥：任意时刻最多一个采集


def read_history(job=None):
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            hist = json.load(f)
    except Exception:
        return []
    if job:
        hist = [h for h in hist if h.get("job") == job]
    return hist


def append_history(entry):
    hist = read_history()
    hist.insert(0, entry)
    try:
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(hist[:HISTORY_KEEP], f, ensure_ascii=False, indent=1)
    except Exception as e:
        log(f"ERROR: history write failed: {e}")


def _trim_logs(job):
    files = sorted(
        (f for f in os.listdir(os.path.join(LOG_ROOT, job)) if f.endswith(".log")),
        reverse=True,
    )
    for old in files[LOG_KEEP:]:
        try:
            os.remove(os.path.join(LOG_ROOT, job, old))
        except OSError:
            pass


def _kill_group(proc):
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        return
    for _ in range(10):
        if proc.poll() is not None:
            return
        time.sleep(1)
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        pass


def run_job(job, trigger):
    """执行一次采集（阻塞），完成或超时后记录历史、重排下次触发。"""
    state = _states[job]
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = os.path.join(LOG_ROOT, job)
    os.makedirs(log_dir, exist_ok=True)
    log_file = f"{ts}.log"
    log_path = os.path.join(log_dir, log_file)

    state.running = {"started_at": datetime.now().isoformat(timespec="seconds"), "trigger": trigger, "log_file": log_file}
    state.next_run = None
    log(f"job {job} start ({trigger}) -> {log_file}")

    started_at = state.running["started_at"]
    started = time.time()
    exit_code = -1
    try:
        with open(log_path, "ab") as lf:
            lf.write(f"[panel] job={job} trigger={trigger} started={state.running['started_at']}\n".encode())
            lf.flush()
            proc = subprocess.Popen(
                ["bash", os.path.join(REPO_ROOT, "scripts", "run-crawl.sh"), job],
                cwd=REPO_ROOT, stdout=lf, stderr=subprocess.STDOUT,
                start_new_session=True,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
            state.proc = proc
            try:
                exit_code = proc.wait(timeout=RUN_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                log(f"job {job} TIMEOUT after {RUN_TIMEOUT_SECONDS}s, killing")
                _kill_group(proc)
                exit_code = -1
                with open(log_path, "ab") as lf2:
                    lf2.write(f"[panel] TIMEOUT after {RUN_TIMEOUT_SECONDS}s, process group killed\n".encode())
    except Exception as e:
        log(f"ERROR: job {job} launch failed: {e}")
        try:
            with open(log_path, "ab") as lf:
                lf.write(f"[panel] launch failed: {e}\n".encode())
        except OSError:
            pass
    finally:
        state.proc = None
        state.running = None
        duration = round(time.time() - started, 1)
        append_history({
            "job": job, "trigger": trigger, "exit_code": exit_code, "duration_s": duration,
            "started_at": started_at,
            "ended_at": datetime.now().isoformat(timespec="seconds"), "log_file": log_file,
        })
        _trim_logs(job)
        state.cfg = load_config()["jobs"][job]
        state.next_run = compute_next_run(state.cfg)
        log(f"job {job} exit={exit_code} duration={duration}s next={state.next_run}")


def scheduler_loop():
    while True:
        try:
            cfg = load_config()
            for name in JOBS:
                st = _states[name]
                if st.running:
                    continue
                st.cfg = cfg["jobs"][name]
                if st.next_run is None:
                    st.next_run = compute_next_run(st.cfg)
                    continue
                if st.cfg["enabled"] and datetime.now() >= st.next_run:
                    if _run_lock.acquire(blocking=False):
                        # 拿到全局锁才开跑；没拿到说明另一 job 在跑，下轮再试
                        st.next_run = None
                        threading.Thread(
                            target=_run_and_release, args=(name, "scheduled"), daemon=True
                        ).start()
        except Exception as e:
            log(f"ERROR: scheduler loop: {e}")
        time.sleep(POLL_SECONDS)


def _run_and_release(job, trigger):
    try:
        run_job(job, trigger)
    finally:
        _run_lock.release()


def trigger_manual(job):
    state = _states[job]
    if state.running:
        return False, "已有采集在执行中"
    if not _run_lock.acquire(blocking=False):
        return False, "另一任务正在执行（全局串行），请稍后再试"
    st_cfg = load_config()["jobs"][job]
    state.cfg = st_cfg
    threading.Thread(target=_run_and_release, args=(job, "manual"), daemon=True).start()
    return True, "已触发"


# ---------------------------------------------------------------- HTTP

def _repo_head():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT,
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or "?"
    except Exception:
        return "?"


def _load_token():
    """面板 API token（setup-panel.sh 生成于 .panel-token）。

    浏览器不会把缓存的基本认证附加到页面 fetch() 上（Chromium/Safari 实测 401），
    故 API 鉴权不依赖 Authorization 头：token 由服务端注入登录后才能拿到的
    index.html，页面 JS 以 X-Panel-Token 头回传——安全边界与 basicauth 等价。
    """
    try:
        with open(TOKEN_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def _token_ok(handler):
    import hmac
    token = _load_token()
    if not token:
        return False
    given = handler.headers.get("X-Panel-Token") or ""
    if not given:
        _, _, query = handler.path.partition("?")
        for part in query.split("&"):
            if part.startswith("token="):
                given = part[len("token="):]
                break
    return hmac.compare_digest(given.encode(), token.encode())


LOGIN_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>登录 · KPL 采集调度面板</title>
<style>
  :root { --bg:#0f1420; --card:#1a2130; --line:#2a3346; --fg:#e8ecf4; --dim:#8b95a9; --acc:#4f8ef7; --bad:#e05d5d; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--fg);
         font:15px/1.6 system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
         display:flex; align-items:center; justify-content:center; min-height:100vh; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px;
          padding:32px 34px; width:min(360px, 92vw); }
  h1 { font-size:18px; margin:0 0 4px; }
  .sub { color:var(--dim); font-size:13px; margin-bottom:18px; }
  label { font-size:13px; color:var(--dim); display:block; margin-bottom:5px; }
  input { background:#111726; color:var(--fg); border:1px solid var(--line); border-radius:8px;
          padding:9px 12px; font-size:15px; width:100%; }
  input:focus { outline:1px solid var(--acc); }
  button { background:var(--acc); color:#fff; border:0; border-radius:8px;
           padding:9px 0; font-size:15px; width:100%; margin-top:14px; cursor:pointer; }
  .err { color:var(--bad); font-size:13px; min-height:18px; margin-top:10px; }
</style>
</head>
<body>
  <form class="card" method="post" action="/login">
    <h1>KPL 采集调度面板</h1>
    <div class="sub">请输入面板密码登录</div>
    <label for="password">密码</label>
    <input type="password" id="password" name="password" autofocus autocomplete="current-password">
    <button type="submit">登 录</button>
    <div class="err">__ERROR__</div>
  </form>
</body>
</html>
"""


def _load_password():
    try:
        with open(PASSWORD_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def _sign(payload: str) -> str:
    import hashlib
    import hmac as hmac_mod
    secret = _load_token() or "kpl-panel"
    return hmac_mod.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _cookie_ok(handler):
    """会话 cookie 校验：kpl_session=<过期时间戳>.<hmac 签名>（无状态，重启不失效）。"""
    import time
    raw = handler.headers.get("Cookie") or ""
    for part in raw.split(";"):
        part = part.strip()
        if not part.startswith("kpl_session="):
            continue
        value = part[len("kpl_session="):]
        exp_str, _, sig = value.partition(".")
        if not exp_str or not sig:
            return False
        try:
            exp = int(exp_str)
        except ValueError:
            return False
        import hmac as hmac_mod
        if not hmac_mod.compare_digest(_sign(exp_str).encode(), sig.encode()):
            return False
        return exp > int(time.time())
    return False


def _authed(handler):
    return _cookie_ok(handler) or _token_ok(handler)


class Handler(BaseHTTPRequestHandler):
    server_version = "kpl-cron-panel/1.0"

    def log_message(self, fmt, *args):
        log(f"{self.address_string()} {fmt % args}")

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _text(self, text, code=200):
        body = text.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path, _, query = self.path.partition("?")
        if path == "/" or path == "/index.html":
            if not _authed(self):
                body = LOGIN_PAGE.replace("__ERROR__", "")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body.encode())))
                self.end_headers()
                self.wfile.write(body.encode())
                return
            try:
                with open(INDEX_HTML, "r", encoding="utf-8") as f:
                    body = f.read().replace("__PANEL_TOKEN__", _load_token()).encode()
            except OSError:
                return self._text("index.html missing", 500)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if not _authed(self):
            return self._json({"error": "unauthorized"}, 401)
        if path == "/api/healthz":
            return self._json({"ok": True})
        if path == "/api/status":
            jobs = {}
            for name in JOBS:
                st = _states[name]
                st.cfg = load_config()["jobs"][name]
                if st.next_run is None and not st.running:
                    st.next_run = compute_next_run(st.cfg)
                jobs[name] = st.status()
            return self._json({
                "server_time": datetime.now().isoformat(timespec="seconds"),
                "repo_head": _repo_head(),
                "jobs": jobs,
            })
        m = re.fullmatch(r"/api/jobs/(main|schedule)/log", path)
        if m:
            job = m.group(1)
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            log_dir = os.path.join(LOG_ROOT, job)
            name = params.get("name", "")
            if name and not re.fullmatch(r"[0-9]{8}-[0-9]{6}\.log", name):
                return self._json({"error": "bad log name"}, 400)
            if not name:
                files = sorted((f for f in os.listdir(log_dir) if f.endswith(".log")), reverse=True) if os.path.isdir(log_dir) else []
                if not files:
                    return self._text("（暂无日志）")
                name = files[0]
            full = os.path.join(log_dir, name)
            try:
                with open(full, "rb") as f:
                    f.seek(0, os.SEEK_END)
                    size = f.tell()
                    f.seek(max(0, size - LOG_TAIL_BYTES))
                    data = f.read().decode("utf-8", "replace")
            except OSError:
                return self._text("日志不存在", 404)
            return self._text(data)
        return self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == "/login":
            return self._handle_login()
        if not _authed(self):
            return self._json({"error": "unauthorized"}, 401)
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return self._json({"error": "bad json"}, 400)
        m = re.fullmatch(r"/api/jobs/(main|schedule)/config", self.path)
        if m:
            job = m.group(1)
            try:
                valid = _validate_job_cfg(job, body)
            except ValueError as e:
                return self._json({"error": str(e)}, 400)
            cfg = load_config()
            cfg["jobs"][job] = valid
            save_config(cfg)
            st = _states[job]
            st.cfg = valid
            if not st.running:
                st.next_run = compute_next_run(valid)
            log(f"job {job} config updated: {valid}")
            return self._json({"ok": True, "config": valid})
        m = re.fullmatch(r"/api/jobs/(main|schedule)/run", self.path)
        if m:
            ok, msg = trigger_manual(m.group(1))
            return self._json({"ok": ok, "message": msg}, 200 if ok else 409)
        return self._json({"error": "not found"}, 404)

    def _handle_login(self):
        """表单登录：密码正确则种 7 天会话 cookie 并跳回面板。"""
        from urllib.parse import parse_qs
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8", "replace") if length else ""
        given = parse_qs(body).get("password", [""])[0]
        expected = _load_password()
        if not expected or not given:
            return self._login_page("密码不能为空")
        if not hmac.compare_digest(given.encode(), expected.encode()):
            time.sleep(1)  # 拖慢爆破
            return self._login_page("密码错误")
        exp = str(int(time.time()) + 7 * 24 * 3600)
        cookie = f"kpl_session={exp}.{_sign(exp)}; Path=/; HttpOnly; SameSite=Lax; Max-Age=604800"
        self.send_response(302)
        self.send_header("Location", "/")
        self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _login_page(self, error=""):
        body = LOGIN_PAGE.replace("__ERROR__", error)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body.encode())))
        self.end_headers()
        self.wfile.write(body.encode())


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    os.makedirs(LOG_ROOT, exist_ok=True)
    for job in JOBS:
        os.makedirs(os.path.join(LOG_ROOT, job), exist_ok=True)
    cfg = load_config()
    for name in JOBS:
        _states[name].cfg = cfg["jobs"][name]
        _states[name].next_run = compute_next_run(cfg["jobs"][name])
        log(f"job {name}: enabled={_states[name].cfg['enabled']} mode={_states[name].cfg['mode']} next={_states[name].next_run}")
    threading.Thread(target=scheduler_loop, daemon=True).start()
    log(f"serving on http://{BIND}:{PORT} (repo: {REPO_ROOT})")
    Server((BIND, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
