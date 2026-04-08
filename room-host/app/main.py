import os
import platform
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psutil

app = FastAPI(title='Lobster Room Host')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.get('/health')
def health():
    return {'ok': True, 'room': 'host', 'time': datetime.now().isoformat()}

@app.get('/system')
def system_info():
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    return {
        'hostname': platform.node(),
        'os': platform.platform(),
        'cpu_percent': psutil.cpu_percent(interval=0.3),
        'memory': {
            'total_mb': round(vm.total / 1024 / 1024, 1),
            'used_mb': round(vm.used / 1024 / 1024, 1),
            'percent': vm.percent
        },
        'disk_root': {
            'total_gb': round(disk.total / 1024 / 1024 / 1024, 2),
            'used_gb': round(disk.used / 1024 / 1024 / 1024, 2),
            'percent': disk.percent
        },
        'loadavg': os.getloadavg() if hasattr(os, 'getloadavg') else None
    }
