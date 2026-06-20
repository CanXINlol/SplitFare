# SplitFare — Phase 0 MVP

本地可运行的机票拆票演示。它比较 protected itinerary 与 split-ticket / self-transfer itinerary，仅使用固定 mock 数据，不代表实时票价或真实可售库存。

## 功能

- 单程 MEL → PVG 或 MEL → SHA 搜索
- 候选中转：BKK、SIN、KUL、HKG、TPE、ICN、NRT、CAN
- 后端严格按用户的最小/最大 gap（含边界）过滤
- protected baseline、cheapest split、safest split 和风险调整后的完整排名
- 展示总价、相对 baseline 的节省、风险、gap、总耗时、供应商、更新时间和过期时间
- self-transfer 显著显示误机、行李、费用、签证/入境风险
- 可插拔 `FlightSupplier` adapter；Phase 0 实现为确定性 mock supplier

## Setup

需要 Docker Desktop（推荐）；或 Node.js 22+、Python 3.12+。

### Docker 一条命令

```bash
docker compose up --build
```

打开 <http://localhost:3000>。API 文档在 <http://localhost:8000/docs>。

### 分别启动

后端：

```bash
cd backend
python -m venv .venv
# PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

前端（另一个终端）：

```bash
cd frontend
npm install
npm run dev
```

如 API 地址不同，启动前设置 `NEXT_PUBLIC_API_URL`。任何未来的 supplier key 必须只存放在后端环境变量，不能使用 `NEXT_PUBLIC_` 前缀。

## Test

```bash
cd backend
pytest

cd ../frontend
npm test
npm run build
```

后端测试覆盖搜索结果数量、split 数量、gap 过滤、self-transfer 风险下限和警告、乘客价格缩放及 API camelCase 契约。前端组件测试覆盖验收要求中的价格、节省、风险、gap、耗时与风险提示显示。

## API 示例

`POST /api/search`

```json
{
  "origin": "MEL",
  "destination": "PVG",
  "departureDate": "2026-08-12",
  "minGapHours": 3,
  "maxGapHours": 12,
  "passengers": 1,
  "cabin": "economy",
  "maxResults": 20,
  "sort": "value",
  "checkedBaggageLikelyRequired": false,
  "visaTransitRequirementUnknown": true
}
```

所有价格均包含 `currency`、供应商、`lastCheckedAt` 与 `expiresAt`。mock 的 checked/expiry 时间基于搜索日期固定生成，以保证测试可重复。

## Phase 1 数据模型设计

前后端共享同一套 camelCase API 契约；Python 内部使用 snake_case，并由 Pydantic alias 自动序列化。对应定义位于 `backend/app/models.py` 与 `frontend/lib/types.ts`。

```text
FlightSupplier
  └─ NormalizedFlightOffer[]  # 一份可购买报价：价格、币种、supplier、时效、raw payload
       └─ Segment[]           # 实际承运航段：机场、时间、航司、航班号

Itinerary
  ├─ offers[]                 # protected 通常 1 份；split-ticket 通常多份
  ├─ segments[]               # offers 内 segments 的有序扁平视图
  └─ RiskAssessment           # score、level、warnings
```

`Supplier`、`ItineraryType`、`RiskLevel` 和 `Cabin` 都是封闭 enum。供应商 adapter 必须先构造 `NormalizedFlightOffer`，才能把数据交给搜索服务。Pydantic 会拒绝未知字段、缺少价格/币种/时间、非正价格、无时区或逆序时间、失效的 IATA/currency 格式、已过期的报价时效关系，以及与内部 segments 首尾不一致的 offer。当前策略是“拒绝 invalid”，不会让部分无效报价进入排名。

`rawPayload` 在 Phase 1 mock API 中保留，用于证明归一化来源与调试。接入真实供应商时必须在 adapter 层清除密钥、个人数据和供应商禁止透传的字段，不能把未经清洗的 payload 返回浏览器。

## Phase 2 Split-ticket matching

核心算法是 `backend/app/matching.py` 中的 pure function：

```python
result = match_flight_offers(MatchingRequest(
    origin="MEL",
    destination="PVG",
    departure_date=date(2026, 8, 12),
    min_gap_minutes=180,
    max_gap_minutes=720,
    max_results=10,
    offers=tuple(normalized_offers),
    sort="value",  # 或 cheapest
))
```

它只读取请求数据，不调用 supplier、数据库、缓存或网络，也不修改输入 offers。输出包含 `protectedItineraries`、`splitTicketItineraries`、可空的 `baselinePrice` 和受 `maxResults` 限制的 `rankedResults`。API 为兼容现有 UI 还保留 `baseline`、`cheapestSplit`、`safestSplit` 和 `ranked` 视图。

匹配规则：

- 搜索日期当天出发的 A→B normalized offer 形成 protected baseline，最低价为 baseline price。
- A→X 与 X→B 的两个独立 offers 可形成 split-ticket，第二段必须严格晚于第一段到达。
- gap 的最小值与最大值均包含边界；total duration 从第一段出发计算到末段到达。
- 没有 protected offer 时仍可返回 split 结果，但 `baselinePrice` 与 `savingsVsBaseline` 为 `null`。
- 输入出现多个币种会整体拒绝；Phase 2 不进行隐式汇率换算。
- 相同的有序 offer ID 组合只保留一次；排序最终以稳定 itinerary ID 打破平局。

默认 `valueScore` 为 0–100：

```text
45% × normalized positive savings
30% × inverse risk
15% × inverse relative duration
10% × convenience
```

convenience 中 protected 为 1，同机场 self-transfer 为 0.75，超过 12 小时的 layover 为 0.5，跨机场为 0。`sort=cheapest` 时改为 total price 优先，并用 duration、risk、ID 做稳定 tie-break。

目前只把已知同城机场组识别为跨机场候选（PVG/SHA、NRT/HND、LHR/LGW/STN）。这类结果不计算地面交通时间或费用，强制至少 high risk，并显示 ground-transfer 警告。算法仍只支持一次中转和单个出发日期。

## Phase 3 Risk Engine

`backend/app/risk.py` 是独立的 pure Risk Engine。protected itinerary 从 10 分开始，split-ticket 从 45 分开始，再根据 gap、overnight、跨机场、行李信息、supplier、airline、低成本航司、未知签证/过境要求和凌晨航班逐项加分，最终封顶 100。

| 分数 | 等级 |
| --- | --- |
| 0–25 | low |
| 26–55 | medium |
| 56–80 | high |
| 81–100 | extreme |

每个 split-ticket 至少包含以下两条提示：

- `This is a self-transfer itinerary.`
- `Your second ticket may not be protected if the first flight is delayed.`

`checkedBaggageLikelyRequired` 和 `visaTransitRequirementUnknown` 是显式风险上下文，默认分别为 `false` 和 `true`。系统不会推断具体国家的签证政策，不保证行李直挂，也不保证任何航司或供应商保护第二张票。相关 warning 只表示需要旅客进一步核实。

`riskScore` 是帮助比较候选行程的一致性启发指标，不是安全、签证、入境、行李或衔接可行性的保证。默认 value 排序会把 extreme 结果放在所有非 extreme 结果之后；只有显式使用 `sort=cheapest` 时，extreme 低价结果才可能排在首位。

## Known limitations

- 所有航班、价格和供应商均为虚构 mock；不连接真实 API、不爬站、不验证库存。
- 仅支持 MEL → PVG/SHA、单程和最多一次中转；没有多日期搜索。
- cabin 会进入标准化结果，但 Phase 0 mock 价格不随 cabin 变化。
- 风险评分是解释性启发规则，不保证签证、入境、过境、行李直挂、航站楼交通或衔接可行。
- 不提供登录、支付、预订、价格提醒、数据库或缓存。
- Mock 数据暂时没有跨机场组合；算法可识别有限同城机场组，但不计算 ground transfer 时间或费用。
- 真实购买流程必须在跳转/付款前重新验证价格，本 demo 没有购买入口。

## 下一阶段建议

在保持 supplier adapter 边界的前提下，先接入一个有授权的 sandbox API；增加报价重新验证、机场/时区数据库和 Playwright E2E，再考虑 PostgreSQL 搜索历史与 Redis 缓存。不要在 Phase 1 同时引入支付。
