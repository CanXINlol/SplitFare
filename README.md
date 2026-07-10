# SplitFare

SplitFare 是一个本地可运行的拆票搜索 Release Candidate。它用确定性的 mock 航班数据对比普通联程保护票与一次中转的 self-transfer 组合，展示价格、节省金额、耗时、风险、供应商和验价状态。它不售票，也不代表实时库存。

## 当前产品行为

- 出发地和目的地只能通过“大洲 → 国家/地区 → 城市”选择；不接受自由文本或 IATA 输入。
- 前端提交稳定的 `originCityId` / `destinationCityId`，后端将城市解析成最多 3 个机场并生成机场搜索矩阵。
- 支持 protected、split-ticket、gap filtering、value/cheapest 排序、风险评估和 pre-booking mock verification。
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
- 可选 `DATABASE_URL`, `REDIS_URL`

不要把任何 token 放进 `NEXT_PUBLIC_*`。

## API

- `GET /health`
- `GET /api/cities`：版本化的 Continent/Country/City 目录
- `POST /api/search`：只接受 city IDs，不接受 `origin`、`destination`、airport ID 或旧 place ID
- `POST /api/booking-options/verify`：使用 `searchId`、`itineraryId`、`bookingOptionId`
- `POST /api/offers/{supplier}/{offer_id}/verify`

错误响应统一为：

```json
{"error":{"code":"validation_error","message":"...","requestId":"..."}}
```

前端按稳定 `code` 翻译用户文案；生产环境不返回 raw stack trace。`rawPayload` 默认不传给前端，只有非生产环境显式 `debug=true` 才可查看。

## 缓存

航班缓存键为 `flight:v2:*`，指纹包含：origin/destination city IDs、解析后的两端机场集合、日期、乘客、舱位、min/max gap、币种与 supplier mode。语言不参与搜索缓存。Redis 不可用时搜索仍能工作。旧 autocomplete、place resolve 和 candidate-hub 缓存已删除。

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

## 部署

前端可部署到 Vercel，设置 HTTPS `NEXT_PUBLIC_API_BASE_URL`。后端 Dockerfile 可用于 Render、Fly.io 或 Railway，设置明确的 `FRONTEND_ORIGIN`、`APP_ENV=production` 与 `ENABLE_MOCK_SUPPLIER=true`。详细步骤见 `docs/DEPLOYMENT.md`。

## 数据模型

后端 Pydantic 与前端 TypeScript 对齐：CityCatalog、SearchRequest、NormalizedFlightOffer、Segment、Itinerary、RiskAssessment、BookingOption、PriceStatus 和 VerifyPriceResult。后端负责价格、总耗时、节省金额、风险与排序；前端只负责展示和 locale 格式化。

## 已知限制

- 所有航班和 confirmed 状态均来自 mock supplier，并明确标注为 demo；不是实时价格或库存。
- Trip.com/Skyscanner 仅为 redirect-only 能力示例，不能参与 confirmed 最低价。
- 不支付、不出票、不登录、不做价格提醒、多日期、真实签证判断或地面交通成本。
- 只支持 seed 城市、单程、最多一次中转；城市机场最多取优先级最高的 3 个。
- verification 只验证确定性 mock 状态；无安全外链时不会继续跳转。
