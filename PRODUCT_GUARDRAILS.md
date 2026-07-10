# SplitFare Product Guardrails

## 核心问题

SplitFare 帮助用户比较 protected/through-ticket 与 split-ticket/self-transfer 的价格、耗时和风险。它不是普通航班列表，也不是 OTA 克隆。

用户输入地点、日期、乘客、舱等和 layover gap；系统解析机场集合，查询已授权 supplier，标准化 offer，组合最多一次中转的 itinerary，并解释便宜的代价与购买路径。

## 支持范围

- seed city/airport autocomplete 与中英文 alias
- city → prioritized airports；airport → single airport
- 单程、单一出发日期、最多一次中转
- protected 与 split-ticket 比较
- same-airport transfer；显式建模的 cross-airport transfer 仅作高风险展示
- supplier capability routing、partial failure、timeout、cache fallback
- mock verification 与 redirect-only provider handoff

## 不支持范围

- 未授权网页抓取、验证码/登录/风控绕过
- 真实支付、出票、退改、登录、账户、价格提醒
- 完整地址、POI、酒店、用户定位、国家级搜索
- 真实签证判断、地面交通价格或可行性保证
- 多日期价格范围搜索

## PriceStatus

- `confirmed`：source 明确返回且尚未过期。Mock 中只表示 demo contract 内确认。
- `cached`：来自缓存或已超过确认窗口，显示 `last_checked_at` 并要求复核。
- `estimated`：非确定价格，不参与 confirmed cheapest。
- `redirect_only`：只有安全 provider URL，不携带确定价格，不参与 itinerary pricing/ranking。
- `unavailable`：禁用继续购买。

`PriceStatus` 是唯一价格状态来源；不得再引入平行的 confidence enum。

## Self-transfer 定义

Split-ticket 由至少两张独立订单组成。必须显著显示：

- `This is a self-transfer itinerary.`
- 前序延误时后续机票可能不受保护
- 可能需要提取并重新托运行李
- transit/visa requirement unknown
- overnight、long layover 或 cross-airport 风险（如适用）

不得把两张独立订单描述为 protected connection。

## Mock / live 边界

- local/test 可启用 mock。
- production demo 必须显式启用 mock，并在 API metadata 与 UI 显示 Demo Data。
- production live 默认禁用 mock，不得静默 fallback 或把 mock 混入 live ranking。
- mock adapter 必须 `supports_live_price=false`。
- mock verification 不得描述为真实 supplier verification。

## 禁止营销承诺

禁止使用“全网最低价”“guaranteed cheapest”“保证衔接”“保证行李直挂”“保证可入境/过境”等文案。允许的表述是“当前已接入供应商中找到的结果”。

## Supplier 接入规则

- API key 只在后端读取。
- Orchestrator 只能通过 `SupplierAdapter` 与 capability routing 调用 supplier。
- 每个 search result 必须 normalize；单个 supplier 失败不能导致整体 500。
- timeout、rate limit、auth、invalid response 使用标准错误且清理 token/header。
- `supports_search=false` 不得调用 search；`supports_price_verify=false` 不得调用 verify。
- redirect-only supplier 不生成 fare offer 或虚构价格。
- booking URL 只允许 HTTP(S)，外部 URL 使用 HTTPS，且 verification 必须使用 server-side canonical URL。

## 不可破坏原则

1. 用户输入地点，核心搜索使用机场集合。
2. gap 使用 timezone-aware datetime 的真实时间差。
3. 不同币种在无 FX 层时拒绝组合。
4. 总价、风险与 ranking 由后端计算。
5. extreme risk 默认不能成为 best overall。
6. raw payload 默认不返回前端，production 禁止 debug raw payload。
7. 不保存护照、卡号或不必要敏感数据。
8. 新算法规则必须同步测试与本文件。
