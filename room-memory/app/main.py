import os
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Lobster Room Memory")
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
WORKSPACE = Path('/copaw-workspace')
LONG_MEMORY = WORKSPACE / 'MEMORY.md'
DAY_MEMORY_DIR = WORKSPACE / 'memory'
ADMIN_TOKEN = os.getenv('LOBSTER_ADMIN_TOKEN', 'change-me')


class AppendPayload(BaseModel):
    text: str


def require_admin(x_admin_token: str | None):
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail='unauthorized: invalid x-admin-token')


@app.get('/health')
def health():
    return {'ok': True, 'room': 'memory', 'time': datetime.now().isoformat()}


@app.get('/memory/overview')
def overview():
    if not WORKSPACE.exists():
        raise HTTPException(status_code=500, detail='CoPaw workspace not mounted')

    daily_files = []
    DAY_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    for p in sorted(DAY_MEMORY_DIR.glob('*.md')):
        daily_files.append({'name': p.name, 'size': p.stat().st_size})

    return {
        'workspace': str(WORKSPACE),
        'long_memory_exists': LONG_MEMORY.exists(),
        'daily_count': len(daily_files),
        'daily_files': daily_files[-15:],
    }


@app.get('/memory/long')
def read_long_memory():
    if not LONG_MEMORY.exists():
        return {'exists': False, 'content': ''}
    return {'exists': True, 'content': LONG_MEMORY.read_text(encoding='utf-8')}


@app.get('/memory/daily/{date_str}')
def read_daily(date_str: str):
    target = DAY_MEMORY_DIR / f'{date_str}.md'
    if not target.exists():
        raise HTTPException(status_code=404, detail='daily note not found')
    return {'exists': True, 'file': target.name, 'content': target.read_text(encoding='utf-8')}


@app.post('/memory/long/append')
def append_long_memory(payload: AppendPayload, x_admin_token: str | None = Header(default=None)):
    require_admin(x_admin_token)
    LONG_MEMORY.parent.mkdir(parents=True, exist_ok=True)
    if not LONG_MEMORY.exists():
        LONG_MEMORY.write_text('', encoding='utf-8')
    with LONG_MEMORY.open('a', encoding='utf-8') as f:
        f.write('\n' + payload.text.rstrip() + '\n')
    return {'ok': True, 'file': str(LONG_MEMORY), 'appended_chars': len(payload.text)}


@app.post('/memory/daily/{date_str}/append')
def append_daily(date_str: str, payload: AppendPayload, x_admin_token: str | None = Header(default=None)):
    require_admin(x_admin_token)
    if '/' in date_str or '..' in date_str:
        raise HTTPException(status_code=400, detail='invalid date string')

    DAY_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    target = DAY_MEMORY_DIR / f'{date_str}.md'

    if not target.exists():
        target.write_text(f'# {date_str}\n\n', encoding='utf-8')

    timestamp = datetime.now().strftime('%H:%M:%S')
    with target.open('a', encoding='utf-8') as f:
        f.write(f'- [{timestamp}] {payload.text.rstrip()}\n')

    return {'ok': True, 'file': target.name, 'appended_chars': len(payload.text)}
