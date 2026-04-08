import os
import subprocess
import urllib.request
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
RESTART_BRIDGE_URL = 'http://host.docker.internal:19191/restart-copaw'


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


@app.get('/skills/list')
def skills_list():
    return run_cmd([COPAW_BIN, 'skills', 'list'])


@app.get('/models/list')
def models_list():
    return run_cmd([COPAW_BIN, 'models', 'list'])
