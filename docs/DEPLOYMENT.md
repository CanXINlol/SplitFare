# Deployment Guide

SplitFare 当前主产品是零成本路线发现与浏览器本地手动比价。生产前端调用 `/api/routes/discover`，该接口不需要航班供应商凭证、不抓取第三方页面，也不返回实时价格。旧 supplier 模式仅为隔离的兼容能力。

生产发布应保持第三方平台入口为公开 HTTPS 搜索页，并在发布前人工复核 `backend/app/data/provider_search.py`。不要把旧 `/api/search` 的 Mock 价格重新接回当前结果页。

## Deployment modes

| Mode | `APP_ENV` | `ENABLE_MOCK_SUPPLIER` | `DUFFEL_MODE` | 行为 |
| --- | --- | --- | --- | --- |
| Local/test | `local` / `test` | `true` | `disabled` | 确定性 demo data |
| Duffel sandbox | 任意 | `false` | `sandbox` | 只接受 `duffel_test_*` token，UI/API 显示 Sandbox |
| Production live | `production` | `false` | `live` | 只接受非 test token，不回退或混入 Mock |

`ENABLE_MOCK_SUPPLIER=true` 与 `DUFFEL_MODE=sandbox|live` 互斥；配置冲突时后端拒绝启动，防止测试价格与真实价格进入同一个排名。

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
DUFFEL_MODE=live
DUFFEL_API_TOKEN=<server-only-secret>
DUFFEL_MAX_RETRIES=1
DUFFEL_CACHE_TTL_SECONDS=600
DUFFEL_ALLOWS_CACHE=false
DUFFEL_BOOKING_ALLOWED_DOMAINS=
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

`DUFFEL_API_TOKEN` 只能存在于后端 secret store。Sandbox 使用 `DUFFEL_MODE=sandbox` 和正式获得的 test token；无凭证时使用 `DUFFEL_MODE=disabled`，服务仍可启动。只有供应商合同明确允许时才将 `DUFFEL_ALLOWS_CACHE` 设为 `true`。

`DUFFEL_BOOKING_ALLOWED_DOMAINS` 默认必须留空。只有 Duffel 实际返回与当前 Offer 绑定、且合同允许向用户跳转的 HTTPS 域名时才加入 allowlist。不要加入通用搜索页、example host 或客户端提交的域名。

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
