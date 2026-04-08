from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import docker

app = FastAPI(title='Lobster Room Docker')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

def client():
    try:
        return docker.from_env()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'docker unavailable: {e}')

@app.get('/health')
def health():
    return {'ok': True, 'room': 'docker', 'time': datetime.now().isoformat()}

@app.get('/containers')
def containers(all: bool = True):
    c = client()
    data = []
    for item in c.containers.list(all=all):
        data.append({
            'name': item.name,
            'status': item.status,
            'image': item.image.tags[0] if item.image.tags else item.image.short_id
        })
    return {'count': len(data), 'items': data}

@app.post('/containers/{name}/restart')
def restart_container(name: str):
    c = client()
    try:
        ct = c.containers.get(name)
        ct.restart()
        return {'ok': True, 'name': name, 'action': 'restart'}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail='container not found')
