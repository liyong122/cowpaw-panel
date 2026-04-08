# CoPaw 龙虾基地（Lobster Base）MVP · 第二轮

## 核心原则
以 CoPaw 为主系统核心，房间化页面作为可视化控制台。

## 服务

- `gateway/` 房间地图入口（Nginx，含实时状态灯）
- `room-copaw/` CoPaw 主控房（FastAPI，封装 copaw CLI）
- `room-memory/` 记忆房（读写 CoPaw 工作区 MEMORY.md + memory/*.md）
- `room-host/` 主系统房（FastAPI + psutil）
- `room-docker/` 容器房（FastAPI + docker sdk）

## 启动

```bash
cd /mnt/hdd/lobster-base
docker compose up -d
```

## 访问

- 房间地图：`http://192.168.1.5:18080`
- CoPaw 主控房：`http://192.168.1.5:18104`
- 记忆房：`http://192.168.1.5:18101`
- 主系统房：`http://192.168.1.5:18102`
- 容器房：`http://192.168.1.5:18103`

## 新增 API（第二轮）

### room-copaw
- `GET /health`
- `GET /daemon/status`
- `GET /daemon/version`
- `GET /daemon/logs?lines=120`
- `POST /daemon/reload-config`（需要 `x-admin-token`）
- `POST /daemon/restart-hint`（需要 `x-admin-token`）
- `POST /daemon/restart-real`（需要 `x-admin-token`，通过宿主机 bridge 真重启 CoPaw）
- `POST /mihomo/restart`（需要 `x-admin-token`，通过宿主机 bridge 重启 mihomo）
- `GET /skills/list`
- `GET /models/list`

### room-memory
- `GET /health`
- `GET /memory/overview`
- `GET /memory/long`
- `GET /memory/daily/{date}`
- `POST /memory/long/append`（需要 `x-admin-token`）
- `POST /memory/daily/{date}/append`（需要 `x-admin-token`）

## 安全

当前示例 token 通过 docker compose 注入：

- `LOBSTER_ADMIN_TOKEN=199200`

请后续改成你自己的随机强口令。
