# SplitFare

SplitFare 是一个零成本拆票路线发现与手动价格比较工具。用户选择大洲、国家和城市后，后端将城市解析为机场集合，根据区域 Hub、地理绕行和结构风险生成候选自助中转路线。应用不抓取第三方页面、不调用付费航班 API，也不展示系统声称的实时或已确认票价。

## 当前产品流程

```text
city_id
→ origin/destination airport sets
→ region-aware Hub selection
→ airport × hub × airport candidate routes
→ great-circle detour + signature dedupe
→ structural/schedule-unknown risk
→ route ranking
→ provider search entry points for each leg
→ user-entered prices in localStorage
→ cost and protected-ticket comparison
```

Melbourne → Shanghai 会解析为 MEL/AVV → 区域 Hub → PVG/SHA。候选路线不包含虚构航班号、精确时刻、供应商库存、确认价格或保证节省金额。

## 路线发现

`POST /api/routes/discover` 是当前前端使用的主接口。它只接受稳定 city IDs、日期、乘客、舱位、建议 gap 和结构排序，不调用 Supplier Adapter。

默认排序选项：

- Best route
- Lowest risk
- Shortest detour
- Simplest transfer

Hub 配置位于 `backend/app/data/route_hubs.py`，按 Oceania → Asia、Europe → Asia、North America → Asia 等区域组合选择。机场坐标的唯一权威来源为 `backend/app/data/airport_geo.py`。大圆距离只用于 detour ratio，不代表飞行时间。

结构风险与依赖时刻的风险分开：Self-transfer、独立订单、换机场和可能重新托运行李属于结构风险；具体 gap、夜间和衔接可行性明确要求用户在平台选择实际航班时确认。

## 平台搜索入口

平台配置集中在 `backend/app/data/provider_search.py`，目前提供 Trip.com、Skyscanner、Google Flights 和适用航段的 Qantas 公开航班搜索首页。

- 所有 URL 由后端生成并要求 HTTPS。
- 不使用 `example.com`，不接受前端 URL。
- 未经正式文档和合作授权，不猜测预填路线参数；此时返回 `manual_search_required`，并展示需要手动输入的机场和日期。
- 跳转后页面不会被 SplitFare 读取、抓取或跟踪。
- 所有自动平台入口语义为 `redirect_only`，不参与价格排名。

Skyscanner 的正式 Affiliates Link API 需要合作伙伴 onboarding 和 `mediaPartnerId`，因此本零成本版本没有伪造 affiliate deep link，只使用公开搜索首页。

## 手动价格比较

用户可以为候选路线输入：

- 两段航班价格
- 行李、座位、支付、跨机场交通、住宿及其他费用
- 可选联程保护票价格

所有计算使用整数 minor units，拒绝负数、超过上限、两位以上小数和混合币种。没有联程票价格时，只显示拆票总成本，不生成 baseline 或节省金额。

数据保存在 `splitfare:manual-comparisons:v1` localStorage 中：

- 支持修改、逐条重置、清除全部和 JSON 导出。
- 页面刷新和语言切换保留记录。
- 损坏数据安全清理。
- 不保存银行卡、支付信息或个人资料。

## 安装与运行

要求 Node.js 20+、Python 3.11+。

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt

cd ..\frontend
npm ci
```

分别运行：

```powershell
# terminal 1
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend
$env:NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"
npm run dev
```

访问 `http://localhost:3000`。健康检查：`http://localhost:8000/health`。

Docker：

```powershell
docker compose up --build
```

## 环境变量

当前路线发现不需要任何航班 API key。

前端：

- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_APP_ENV`

后端：

- `APP_ENV`, `APP_VERSION`, `API_BASE_URL`
- `FRONTEND_ORIGIN`
- `LOG_LEVEL`, `RATE_LIMIT_REQUESTS_PER_MINUTE`
- 可选 `DATABASE_URL`, `REDIS_URL`

Duffel 配置仍为兼容旧实验接口保留，但 `/api/routes/discover` 不读取或调用 Duffel。

## 测试与构建

```powershell
cd backend
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m pytest -q

cd ..\frontend
npm run typecheck
npm run lint
npm run test
npm run test:e2e
npm run build
```

Next 开发缓存使用 `.next`，production build 使用 `.next-production`，运行 dev server 时也可构建。

## 兼容接口

旧 `/api/search`、Supplier Adapter 和 Itinerary 模型暂时保留用于回归与未来合法数据源实验，但当前前端不调用它们。生产路线发现页面不会展示 Mock confirmed price、模拟节省金额或假验价。

## 当前限制

- 没有真实航班时刻、库存或票价。
- 无法判断某条候选路线当天是否实际有合适航班。
- 建议 gap 是用户筛选范围和结构性提示，不是已验证衔接。
- 不判断签证、过境或入境政策。
- 不接 FX API；用户必须统一币种后输入。
- 机场坐标为路线规划参考点，不用于估算飞行时间。
- 平台公开首页可能要求用户重新输入全部搜索条件。
