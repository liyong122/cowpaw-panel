import os
import subprocess
import urllib.request
import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title='Lobster Room CoPaw')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

COPAW_BIN = '/root/.copaw/venv/bin/copaw'
ADMIN_TOKEN = os.getenv('LOBSTER_ADMIN_TOKEN', 'change-me')
RESTART_BRIDGE_URL = os.getenv('RESTART_BRIDGE_URL', 'http://host.docker.internal:19191/restart-copaw')
RESTART_MIHOMO_URL = os.getenv('RESTART_MIHOMO_URL', 'http://host.docker.internal:19191/restart-mihomo')
MIHOMO_API = os.getenv('MIHOMO_API', 'http://192.168.1.5:9097')
MIHOMO_SECRET = os.getenv('MIHOMO_SECRET', '123456')
MIHOMO_HTTP_PROXY = os.getenv('MIHOMO_HTTP_PROXY', 'http://host.docker.internal:7890')


def run_cmd(args: list[str], timeout: int = 30):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return {
            'code': p.returncode,
            'stdout': p.stdout.strip(),
            'stderr': p.stderr.strip(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def require_admin(x_admin_token: str | None):
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail='unauthorized: invalid x-admin-token')


@app.get('/health')
def health():
    return {'ok': True, 'room': 'copaw', 'time': datetime.now().isoformat()}


@app.get('/daemon/status')
def daemon_status():
    return run_cmd([COPAW_BIN, 'daemon', 'status'])


@app.get('/daemon/version')
def daemon_version():
    return run_cmd([COPAW_BIN, 'daemon', 'version'])


@app.get('/daemon/logs')
def daemon_logs(lines: int = 120):
    lines = max(10, min(lines, 1000))
    return run_cmd([COPAW_BIN, 'daemon', 'logs', '-n', str(lines)], timeout=40)


@app.post('/daemon/reload-config')
def daemon_reload_config(x_admin_token: str | None = Header(default=None)):
    require_admin(x_admin_token)
    return run_cmd([COPAW_BIN, 'daemon', 'reload-config'])


@app.post('/daemon/restart-hint')
def daemon_restart_hint(x_admin_token: str | None = Header(default=None)):
    require_admin(x_admin_token)
    return run_cmd([COPAW_BIN, 'daemon', 'restart'])


@app.post('/daemon/restart-real')
def daemon_restart_real(x_admin_token: str | None = Header(default=None)):
    require_admin(x_admin_token)
    try:
        req = urllib.request.Request(
            RESTART_BRIDGE_URL,
            method='POST',
            headers={'x-admin-token': x_admin_token}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode('utf-8', errors='ignore')
            return {
                'code': resp.status,
                'stdout': body,
                'stderr': ''
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'restart bridge failed: {e}')


@app.post('/mihomo/restart')
def mihomo_restart(x_admin_token: str | None = Header(default=None)):
    require_admin(x_admin_token)
    try:
        req = urllib.request.Request(
            RESTART_MIHOMO_URL,
            method='POST',
            headers={'x-admin-token': x_admin_token}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode('utf-8', errors='ignore')
            return {
                'code': resp.status,
                'stdout': body,
                'stderr': ''
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'mihomo restart bridge failed: {e}')


@app.get('/skills/list')
def skills_list():
    return run_cmd([COPAW_BIN, 'skills', 'list'])


@app.get('/models/list')
def models_list():
    return run_cmd([COPAW_BIN, 'models', 'list'])


def _find_latest_delay(proxy_obj: dict | None):
    if not proxy_obj:
        return None
    history = proxy_obj.get('history') or []
    if history:
        return history[-1].get('delay')
    extra = proxy_obj.get('extra') or {}
    for _, val in extra.items():
        h = (val or {}).get('history') or []
        if h:
            return h[-1].get('delay')
    return None


def _resolve_final_proxy_name(proxies: dict, start_name: str | None):
    """Follow Selector/URLTest/Fallback chains and return the final leaf node name."""
    if not start_name:
        return None
    seen = set()
    cur = start_name
    for _ in range(8):
        if not cur or cur in seen:
            break
        seen.add(cur)
        obj = proxies.get(cur) or {}
        t = obj.get('type')
        nxt = obj.get('now')
        if t in ('Selector', 'URLTest', 'Fallback', 'LoadBalance', 'Relay') and nxt:
            cur = nxt
            continue
        break
    return cur


def _google_ip_location_snapshot():
    # 通过 mihomo 代理访问公网 IP 服务，作为“当前出口IP归属”展示
    proxies = {
        'http': MIHOMO_HTTP_PROXY,
        'https': MIHOMO_HTTP_PROXY,
    }
    try:
        r = requests.get('https://ipinfo.io/json', proxies=proxies, timeout=6)
        if not r.ok:
            return {'ok': False, 'error': f'ipinfo http {r.status_code}'}
        j = r.json()
        ip = j.get('ip')
        city = j.get('city')
        region = j.get('region')
        country = j.get('country')
        org = j.get('org')
        loc_text = ', '.join([x for x in [city, region, country] if x]) or (country or '--')
        return {
            'ok': True,
            'ip': ip,
            'location': loc_text,
            'org': org,
            'panel_url': 'http://192.168.1.5:9097/ui/#/proxies'
        }
    except Exception as e:
        return {'ok': False, 'error': str(e)}


@app.get('/lobster/system-status')
def system_status():
    rooms = {
        'copaw': 'http://127.0.0.1:8000/health',
        'memory': 'http://lobster_room_memory:8000/health',
        'host': 'http://lobster_room_host:8000/health',
        'docker': 'http://lobster_room_docker:8000/health'
    }
    status_report = {}
    for name, url in rooms.items():
        try:
            resp = requests.get(url, timeout=2)
            status_report[name] = 'up' if resp.status_code == 200 else 'down'
        except Exception:
            status_report[name] = 'down'

    host_info = {
        'os': None,
        'debian': None,
        'cpu_text': None,
        'cpu_percent': None,
        'memory': None,
    }
    try:
        host_resp = requests.get('http://lobster_room_host:8000/system', timeout=2)
        if host_resp.ok:
            raw = host_resp.json()
            host_info = {
                'os': raw.get('os'),
                'debian': raw.get('debian'),
                'cpu_text': raw.get('cpu_text'),
                'cpu_percent': raw.get('cpu_percent'),
                'memory': raw.get('memory'),
            }
    except Exception:
        pass

    mihomo = _google_ip_location_snapshot()

    return {
        'overall': 'green' if all(v == 'up' for v in status_report.values()) else 'yellow',
        'details': status_report,
        'host': host_info,
        'mihomo': mihomo,
        'timestamp': datetime.now().isoformat()
    }
