# SplitFare

SplitFare 是一个 flight split-ticket / self-transfer 决策 demo。用户输入城市、机场或地点，系统把地点解析成机场集合，比较 protected itinerary 与由两张独立机票组成的 split-ticket itinerary，并显式展示价格状态、节省金额、转机时间与风险。

当前版本只使用确定性的 mock flight data。它不是 OTA，不出票、不收款，也不承诺全网最低价、行李直挂、签证可行性或后续航段保护。

## 当前范围

- 地点 autocomplete：英文、中文 alias、精确 IATA、前缀和包含匹配
- city → prioritized airport set，例如 Melbourne → MEL/AVV
- airport → single-airport set，例如 PVG → PVG
- 有上限的 airport/hub query matrix
- 单程、最多一次中转
- protected 与 split-ticket matching、gap filtering、稳定排序
- risk score、risk level、self-transfer warnings
- mock supplier、supplier capabilities、标准化错误与缓存降级
- confirmed、cached、estimated、redirect_only、unavailable 价格状态
- canonical booking option 与 mock pre-booking verification
- FastAPI、Next.js、SQLite 默认持久化、可选 PostgreSQL/Redis
- Docker 与 production-like 配置

不支持真实航班 API、支付、出票、登录、价格提醒、多日期搜索、真实签证判断或地面交通报价。

## 系统要求

- Node.js 22
- Python 3.12
- Docker Desktop（只在使用 Docker 启动时需要）

## 安装

前端：

```powershell
cd frontend
npm ci
```

后端：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## 本地运行

分别启动后端和前端：

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
cd frontend
$env:NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8000"
$env:NEXT_PUBLIC_APP_ENV="local"
npm run dev
```

打开 `http://localhost:3000`。健康检查为 `GET http://127.0.0.1:8000/health`。

Docker full stack：

```powershell
docker compose up --build
```

前端为 `http://localhost:8080`，后端为 `http://localhost:8000`。Compose 明确使用 local mock mode；backend production image 自身默认禁用 mock。

## 环境变量

Frontend：

| 变量 | 说明 |
| --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | 浏览器调用的 FastAPI base URL；production 必填 |
| `NEXT_PUBLIC_APP_ENV` | `local` 或 `production`；不放 secret |

Backend：

| 变量 | 说明 |
| --- | --- |
| `APP_ENV` | `local`、`test` 或 `production` |
| `APP_VERSION` | `/health` 返回的版本 |
| `API_BASE_URL` | 后端公开地址 |
| `FRONTEND_ORIGIN` | 逗号分隔 CORS allowlist；production 禁止 `*` |
| `ENABLE_MOCK_SUPPLIER` | local/test 默认 true；production 默认 false；production demo 必须显式 true |
| `LOG_LEVEL` | 默认 `INFO`；cache hit/miss 在 `DEBUG` |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `/api/search` 每客户端分钟上限 |
| `MAX_SUPPLIER_QUERIES_PER_SEARCH` | 单次搜索 supplier query 总上限，默认 120 |
| `MAX_CONCURRENT_SUPPLIER_REQUESTS` | supplier 并发上限，默认 8 |
| `DATABASE_URL` | 可选；未配置时使用临时目录 SQLite |
| `REDIS_URL` | 可选；不可用时降级到进程内短期缓存 |
| `DUFFEL_API_TOKEN` | 后端专用；mock mode 下不会启用 live Duffel search |
| `EXTERNAL_API_TIMEOUT_SECONDS` | 外部 supplier timeout |

示例见根目录、frontend 与 backend 的 `.env.example`。任何 supplier token 都不得使用 `NEXT_PUBLIC_` 前缀。

### Mock / production 边界

- development/test：允许 mock。
- production demo：必须显式设置 `ENABLE_MOCK_SUPPLIER=true`，API metadata 与 UI 显示 `Demo Data`。
- production live：`ENABLE_MOCK_SUPPLIER=false`，没有静默 mock fallback。
- mock adapter 的 `supports_live_price=false`。其 `confirmed` 只表示在确定性 demo contract 内确认，不表示真实市场价格。
- redirect-only provider 不生成 flight offer、不提供确定价格，也不参与 cheapest/value ranking。

## 地点输入与机场矩阵

地点数据来自 `backend/app/places.py` 的 seed catalog，不接地图 API。支持 Melbourne/墨尔本、Shanghai/上海、Sydney/悉尼、London、New York、Tokyo、Singapore、Hong Kong、Bangkok 等 Phase 11.5 seed 地点。

示例：

```text
Melbourne → Shanghai
[MEL, AVV] → [PVG, SHA]
MEL → BKK → PVG
```

精确机场只解析该机场；`airport:MEL` 不会偷偷加入 AVV。城市最多取 3 个机场、hub 最多 12 个，并按 supplier query 总上限截断。被截断的 hub 会出现在 `SearchResponse.metadata.excludedAirports`。

第一段按用户选择的 departure date 与出发机场本地时区生成。为了支持 overnight layover，orchestrator 可以查询次日（max gap 超过 24 小时时最多后两日）的第二段；这不是用户可选的日期范围搜索。

## API

- `GET /health`
- `GET /api/places/search?q=`
- `POST /api/places/resolve`
- `POST /api/search`
- `POST /api/offers/{supplier}/{offer_id}/verify`
- `POST /api/booking-options/verify`

`SearchRequest` 只接受 `originPlaceId` 与 `destinationPlaceId`，不再接受旧的自由文本 `origin`/`destination` 字段。

`SearchResponse` 包含 `searchId`、`status`、`results`、`errors`、关键分组、metadata 与 disclaimer。Metadata 包含实际 origin/destination airports、hubs、excluded airports、supplier errors、query counts、price freshness counts 与 mock/live mode。

普通响应递归移除 `rawPayload`。只有非 production 的显式 `debug=true` 可返回 adapter raw payload；production 中 debug 参数无效。

## 价格状态

- `confirmed`：供应商或 mock contract 明确返回且仍在有效期内。
- `cached`：来自缓存或已过确认窗口，必须显示检查时间并再次验证。
- `estimated`：估算值，不参与 confirmed cheapest。
- `redirect_only`：只跳转到 provider，不在 SplitFare 内显示确定价格。
- `unavailable`：不可购买，CTA 禁用。

金额在后端使用 `Decimal` 计算，并在 JSON 中序列化为 number。客户端只负责格式化，不重新计算权威总价或风险分。

## Booking 与 verification

Split-ticket 的 booking option 按每张独立 ticket/offer 建模，卡片总价等于各 ticket price 之和。前端提交的 verification request 只含：

```json
{
  "searchId": "...",
  "itineraryId": "...",
  "bookingOptionId": "..."
}
```

后端从搜索期间登记的 canonical option 读取 supplier、offer、previous price 与 URL，不接受前端注入价格或 redirect URL。不支持验证的 provider 返回 `unsupported`，并明确提示用户只能到 provider 检查价格。

Trip.com 与 Skyscanner 仅为 HTTPS redirect-only options。系统不爬取页面、不绕过登录/CAPTCHA，也不把 redirect 标记为 confirmed price。

## 测试与构建

```powershell
cd backend
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m pytest -q
```

```powershell
cd frontend
npm run typecheck
npm run lint
npm test
npm run build
npm run test:e2e
```

Docker build：

```powershell
docker build -t splitfare-api ./backend
docker compose build
```

Playwright 启动 375px Chromium、Next.js 与 FastAPI，覆盖英文/中文 city search、exact airport、invalid location、empty/partial results、protected vs split、verification unchanged/changed/unavailable 与 redirect-only flow。

## 数据与持久化

默认 SQLite 文件位于系统临时目录。设置 PostgreSQL `DATABASE_URL` 后可运行：

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
.\.venv\Scripts\python.exe scripts\seed_airports.py
```

系统不保存护照、银行卡、完整支付信息或账户 email。持久化 raw payload 会先清理 token/authorization 等敏感字段。

## 当前限制

- 航班和 verification 都是 mock；没有真实 availability、booking 或 ticketing。
- seed place catalog 覆盖有限，不支持地址、酒店、景点、定位或国家级模糊搜索。
- 地面换机场成本不计算；显式 cross-airport itinerary 会标记 high/extreme risk。
- 不判断签证政策，只有 transit/visa unknown 风险提示。
- 进程内 booking registry 适合单实例 demo；多实例部署需要共享、短 TTL 的 server-side registry。
- 内存 rate limiter 适合单实例；多实例 production 应迁移到共享 rate-limit store。
- SQLite/Redis 失败会降级或关闭非关键持久化，但 production 应配置监控。

更多内容见 [产品护栏](PRODUCT_GUARDRAILS.md)、[架构](ARCHITECTURE.md)、[审计报告](AUDIT_REPORT.md)、[部署指南](docs/DEPLOYMENT.md) 与 [发布清单](RELEASE_CHECKLIST.md)。
