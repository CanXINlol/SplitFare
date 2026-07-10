# Deployment Guide

SplitFare 当前可部署为 production-like demo 或 live-mode shell。没有真实 supplier credential 时，production live 会正常返回 empty results，不会静默 fallback 到 mock。

## Deployment modes

| Mode | `APP_ENV` | `ENABLE_MOCK_SUPPLIER` | 行为 |
| --- | --- | --- | --- |
| Local/test | `local` / `test` | `true` | 确定性 demo data |
| Production demo | `production` | `true`（显式） | UI/API 显示 Demo Data；不调用 live Duffel |
| Production live shell | `production` | `false` | 禁用 mock；只调用明确配置且 capability 可用的 supplier |

## Vercel frontend

在 Vercel project settings 配置：

```text
NEXT_PUBLIC_API_BASE_URL=https://api.your-domain.test
NEXT_PUBLIC_APP_ENV=production
```

Build command：`npm run build`；root directory：`frontend`。

`NEXT_PUBLIC_API_BASE_URL` 在 production 必填。不要把 token、数据库 URL 或 supplier secret 放入 `NEXT_PUBLIC_*`。

## Render / Railway / Fly.io backend

Backend root 为 `backend`，Dockerfile 已提供。最小 production live 配置：

```text
APP_ENV=production
APP_VERSION=0.1.0
API_BASE_URL=https://api.your-domain.test
FRONTEND_ORIGIN=https://app.your-domain.test
ENABLE_MOCK_SUPPLIER=false
LOG_LEVEL=INFO
RATE_LIMIT_REQUESTS_PER_MINUTE=120
MAX_SUPPLIER_QUERIES_PER_SEARCH=120
MAX_CONCURRENT_SUPPLIER_REQUESTS=8
```

若明确发布 production demo，唯一变化是：

```text
ENABLE_MOCK_SUPPLIER=true
```

页面将显示 Demo Data，mock capability 仍为 non-live。不要在 production demo 中配置或宣称真实价格。

可选：

```text
DATABASE_URL=postgresql+psycopg://...
REDIS_URL=redis://...
EXTERNAL_API_TIMEOUT_SECONDS=10
```

`DUFFEL_API_TOKEN` 是后端专用的未来/live integration 配置。Mock mode 会强制禁用 Duffel live search，防止 live 与 mock 混合 ranking。

## CORS

Production 必须使用完整 HTTPS origin allowlist，多值以逗号分隔：

```text
FRONTEND_ORIGIN=https://app.your-domain.test,https://preview.your-domain.test
```

Production 启动时如包含 `*` 会失败。CORS 仅允许 GET/POST 与 Content-Type header。

## Docker

Backend：

```powershell
docker build -t splitfare-api ./backend
docker run --rm -p 8000:8000 `
  -e APP_ENV=production `
  -e FRONTEND_ORIGIN=https://app.your-domain.test `
  -e ENABLE_MOCK_SUPPLIER=false `
  splitfare-api
```

Frontend image 要求显式 build arg：

```powershell
docker build -t splitfare-web ./frontend `
  --build-arg NEXT_PUBLIC_API_BASE_URL=https://api.your-domain.test `
  --build-arg NEXT_PUBLIC_APP_ENV=production
```

Local full stack：

```powershell
docker compose up --build
```

Compose 明确使用 local mock mode，并启动 PostgreSQL、FastAPI 与 Next.js。

## Database migration

配置 PostgreSQL 后：

```powershell
cd backend
python -m alembic -c alembic.ini upgrade head
python scripts\seed_airports.py
```

若数据库初始化失败，API 会继续提供非持久化搜索并记录安全错误；production 应监控该状态并在 release gate 验证迁移。

## Health and smoke tests

```powershell
Invoke-RestMethod https://api.your-domain.test/health
```

响应只包含 status、version、mode、timestamp，不包含 secret 或数据库 URL。

部署后至少验证：

1. Production CORS 只允许部署前端。
2. `debug=true` 不返回 raw payload。
3. Production live 不出现 mock result；production demo 显示 Demo Data。
4. 页面 source/bundle 不包含 supplier token。
5. Search rate limit 返回统一 429 error。
6. Redirect-only CTA 显示“无法在 SplitFare 验证价格”。
7. Canonical verification 不接受客户端 URL 或 price。

## Rollback

保留上一 release image/tag。出现 supplier、database 或 cache 故障时可回滚；不要通过悄悄打开 mock 来掩盖 live production 故障。Production demo 必须作为明确发布模式重新配置和标识。
