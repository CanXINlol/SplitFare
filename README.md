# SplitFare

SplitFare 是一个本地可运行的拆票搜索 Release Candidate。它支持确定性 mock 数据，以及一个正式实现的 Duffel Flights API v2 Adapter，用于对比普通联程保护票与一次中转的 self-transfer 组合。它不售票，也不代表价格不会变化。

## 当前产品行为

- 出发地和目的地只能通过“大洲 → 国家/地区 → 城市”选择；不接受自由文本或 IATA 输入。
- 前端提交稳定的 `originCityId` / `destinationCityId`，后端将城市解析成最多 3 个机场并生成机场搜索矩阵。
- 支持 protected、split-ticket、gap filtering、value/cheapest 排序、风险评估和 pre-booking verification。
- 中文和英文覆盖首页、选择器、结果、风险、价格状态、错误、empty/loading 和验价弹窗。
- 语言保存在 `splitfare:locale:v1`；搜索条件保存在 sessionStorage 的 `splitfare:search:v2`。切换语言不会重新搜索航班。

## 城市目录

`backend/app/cities.py` 是城市层级和机场映射的唯一权威数据源，前端通过 `GET /api/cities` 获取目录，不保存另一份映射。当前 seed 覆盖亚洲、大洋洲、欧洲和北美洲 33 个城市，包括 Melbourne → MEL/AVV、Shanghai → PVG/SHA、Beijing → PEK/PKX、Tokyo → HND/NRT、Auckland、Christchurch、Toronto 和 Vancouver。

选择城市后，搜索链路为：

```text
city_id → ResolvedCity.airports → AirportSearchMatrix
        → supplier route queries → matching → risk → ranking → verification
```

每个搜索最多 3 个出发机场、3 个到达机场和 12 个 hub。矩阵按 query budget 截断，不做递归搜索。

## Duffel 供应商模式

当前环境没有 Duffel credential，因此默认运行 `mock`，没有进行或宣称 live/sandbox 外部调用成功。Adapter 已按 Duffel 当前官方 v2 文档实现，并通过保存的合法结构 fixture 与 `httpx.MockTransport` 测试。

- `mock`：`ENABLE_MOCK_SUPPLIER=true`, `DUFFEL_MODE=disabled`；只返回 Mock Supplier 航班。
- `sandbox`：`ENABLE_MOCK_SUPPLIER=false`, `DUFFEL_MODE=sandbox`；要求 `duffel_test_*` token，界面明确显示 Sandbox。
- `live`：`ENABLE_MOCK_SUPPLIER=false`, `DUFFEL_MODE=live`；要求正式授权的 live token，不会静默回退 Mock。
- `disabled` 是 Duffel adapter 状态，不是航班数据模式。

Duffel Adapter 使用服务器端 Bearer 认证、`Duffel-Version: v2`、`POST /air/offer_requests` 和 `GET /air/offers/{id}`。它实现 timeout、一次有限 retry、429/5xx 映射、内部 correlation ID、严格时区与 Decimal normalizer。外部 raw payload 只保留在后端，默认响应会移除。

## 安装

要求：Node.js 20+、npm、Python 3.11+。Docker 为可选。

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt

cd ..\frontend
npm ci
```

## 本地运行

分别启动：

```powershell
# terminal 1
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend
$env:NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"
npm run dev
```

访问 `http://localhost:3000`，健康检查为 `http://localhost:8000/health`。

Docker 全栈：

```powershell
docker compose up --build
```

访问 `http://localhost:8080`。Compose 中 Postgres 用于已有持久化层；Redis 未配置时自动使用安全的进程内降级缓存。

## 环境变量

根目录和前后端均提供 `.env.example`。前端仅使用：

- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_APP_ENV`

后端使用：

- `APP_ENV`, `APP_VERSION`, `API_BASE_URL`
- `FRONTEND_ORIGIN`（生产环境必须明确 allowlist，不能使用 `*`）
- `ENABLE_MOCK_SUPPLIER`, `LOG_LEVEL`
- `RATE_LIMIT_REQUESTS_PER_MINUTE`
- `MAX_SUPPLIER_QUERIES_PER_SEARCH`, `MAX_CONCURRENT_SUPPLIER_REQUESTS`
- `DUFFEL_MODE=disabled|sandbox|live`
- `DUFFEL_API_TOKEN`, `DUFFEL_BASE_URL`, `DUFFEL_API_VERSION`
- `EXTERNAL_API_TIMEOUT_SECONDS`, `DUFFEL_MAX_RETRIES`
- `DUFFEL_CACHE_TTL_SECONDS`, `DUFFEL_ALLOWS_CACHE`
- `DUFFEL_BOOKING_ALLOWED_DOMAINS`（默认留空；只允许合同授权且与 Offer 绑定的 HTTPS 域名）
- 可选 `DATABASE_URL`, `REDIS_URL`

不要把任何 token 放进 `NEXT_PUBLIC_*`。

## API

- `GET /health`
- `GET /api/cities`：版本化的 Continent/Country/City 目录
- `POST /api/search`：只接受 city IDs，不接受 `origin`、`destination`、airport ID 或旧 place ID
- `POST /api/booking-options/verify`：使用 `searchId`、`itineraryId`、`bookingOptionId`
- `POST /api/booking-options/redirect-confirmed`：再次使用三个内部 ID 记录确认并返回后端保存的 canonical URL
- `POST /api/offers/{supplier}/{offer_id}/verify`

错误响应统一为：

```json
{"error":{"code":"validation_error","message":"...","requestId":"..."}}
```

前端按稳定 `code` 翻译用户文案；生产环境不返回 raw stack trace。`rawPayload` 默认不传给前端，只有非生产环境显式 `debug=true` 才可查看。

## 价格与购买选项

`BookingOption` 同时返回 `bookingOptionId`、`offerId`、supplier、价格、`PriceStatus`、查询/过期时间、`supportsPriceVerify` 和后端生成的可信 URL。状态只允许 `confirmed`、`cached`、`estimated`、`redirect_only`、`unavailable`。过期的 confirmed/cached 会变成 unavailable，不再伪装成有效缓存。

购买前状态为 `unchanged`、`increased`、`decreased`、`unavailable`、`expired`、`timeout` 或 `unsupported`。前端只提交 search/itinerary/booking option IDs；旧价格和 URL 均来自服务端 registry。涨价或降价只显示对比，不自动跳转。跳转确认事件失败不会阻止已经由后端授权的 URL。

Phase 16 不再自动添加 Trip.com 或 Skyscanner 选项。Duffel Flights Offer 支持 GET Offer 验价，但当前响应没有与该 Offer 绑定的外部购买链接，因此 Sandbox/Live 可以验价、不能伪造购买跳转。

## 缓存

航班缓存键为 `flight:v3:*`，指纹包含：origin/destination city IDs、解析后的两端机场集合、日期、乘客、舱位、min/max gap、币种、supplier 与 supplier mode。语言不参与搜索缓存。Duffel TTL 可配置，且只有 `DUFFEL_ALLOWS_CACHE=true` 时才保存真实供应商数据。Redis 不可用时搜索仍能工作。

## 测试与构建

```powershell
cd frontend
npm run typecheck
npm run lint
npm run test
npm run test:e2e
npm run build

cd ..\backend
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m pytest tests -q

cd ..
docker compose config --quiet
docker compose build
```

E2E 使用 375px mobile Chromium，覆盖 Melbourne → Shanghai、墨尔本 → 上海、语言切换不重搜、risk warning、partial failure 与 verification。

Next 开发缓存使用 `.next`，production build 使用 `.next-production`，因此本地 dev server 运行时也可稳定执行 `npm run build`。

## 部署

前端可部署到 Vercel，设置 HTTPS `NEXT_PUBLIC_API_BASE_URL`。后端 Dockerfile 可用于 Render、Fly.io 或 Railway，设置明确的 `FRONTEND_ORIGIN`、`APP_ENV=production`，并明确选择 mock、sandbox 或 live。任何 Duffel token 只能配置在后端。详细步骤见 `docs/DEPLOYMENT.md`。

## 数据模型

后端 Pydantic 与前端 TypeScript 对齐：CityCatalog、SearchRequest、NormalizedFlightOffer、Segment、Itinerary、RiskAssessment、BookingOption、PriceStatus 和 VerifyPriceResult。后端负责价格、总耗时、节省金额、风险与排序；前端只负责展示和 locale 格式化。

## 已知限制

- 当前仓库和本机没有 Duffel credential；实际启动默认仍是 mock。
- Duffel sandbox/live 能力已实现并通过 HTTP mock fixture 测试，但尚未用本项目账户进行真实外部 smoke test。
- Trip.com/Skyscanner Adapter skeleton 保留在代码库中，但不加载、不生成结果页 BookingOption，也不参与搜索或排序。
- 不支付、不出票、不登录、不做价格提醒、多日期、真实签证判断或地面交通成本。
- 只支持 seed 城市、单程、最多一次中转；城市机场最多取优先级最高的 3 个。
- Duffel 支持 GET Offer 验价，但本项目不出票且 Duffel 不提供 OTA 式外部 booking URL，因此验价后不会在 SplitFare 内完成购买。
