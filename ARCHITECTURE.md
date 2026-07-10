# SplitFare Architecture

## End-to-end flow

```text
LocationInput
  → GET /api/places/search
  → POST /api/places/resolve
  → AirportSearchMatrix
  → capped FlightQuery plan
  → SupplierOrchestrator / SupplierAdapter
  → NormalizedFlightOffer
  → split-ticket matcher
  → Risk Engine
  → value/cheapest ranking
  → SearchResponse + metadata
  → Results UI / BookingOption
  → canonical verification registry
  → POST /api/booking-options/verify
  → optional HTTPS redirect
```

## Location layer

`PlaceService` 是 seed catalog 的唯一来源。React 不维护地点副本。Matching 顺序为 exact IATA、exact city、alias、startsWith、contains，再按 hub/priority/type 稳定排序。

City resolution 最多返回 3 个按 primary、international、priority、distance、mock coverage 排序的机场。Airport resolution 只返回自身。

## Airport matrix

`build_search_queries` 是无 I/O 的纯函数。Baseline 为 origin airport × destination airport。每个 hub 生成 origin→hub 及 hub→destination 查询；为了支持 overnight gap，第二段可查询次日，max gap >24h 时最多查询后两日。

Matrix 保证 route/date/kind/hub key 唯一，排除 origin/hub/destination 同机场组合，并按 `MAX_SUPPLIER_QUERIES_PER_SEARCH / searchable_adapter_count` 截断。Metadata 返回实际使用与被排除的 hub。

## Search orchestrator

`SearchOrchestrator` 创建有总 timeout 的 route tasks。`SupplierOrchestrator` 只路由 `supports_search=true` 的 adapter，每 leg 每 supplier 最多 30 个 offers，使用 semaphore 限制总并发。Errors 会清理敏感值并稳定排序。

## Supplier adapter and normalizer

`SupplierAdapter.search_one_way` 固定执行 fetch → normalize。统一模型为 `SupplierResult`、`SupplierError`、`NormalizedFlightOffer` 与 `SupplierCapabilities`。

- Mock adapters：可搜索、可 mock verify、非 live。
- Duffel：contract/skeleton；mock mode 强制禁用 live search。
- Trip.com/Skyscanner：redirect-only capabilities，不参与 search 或 ranking。

## Split-ticket engine

Matcher 是 pure function。Direct A→B 成为 protected baseline；A→X 与 X→B 在机场连接、时间、gap 和 currency 合法时组成 split-ticket。

Second legs 按 origin 建索引，复杂度从所有 offers 的盲目 O(n²) 降为与可连接机场 bucket 相关的组合。矩阵和 supplier query 上限构成外层复杂度保护。

## Risk engine

后端是 risk rule 的唯一来源。Base score、gap、overnight、cross-airport、baggage、supplier/airline、LCC、visa unknown 与 early/late 时间共同得分，clamp 到 0–100，再由统一边界映射 risk level。前端只显示分数与 warnings。

## Ranking

默认 value score：savings 45%、risk inverse 30%、duration 15%、convenience 10%。Extreme risk 在 value sort 中先降级；只有 `sort=cheapest` 才以价格为第一排序键。所有 tie-breakers 都稳定。

## Price freshness and cache

Flight cache key 包含 supplier、route、date、passengers、cabin、currency。缓存反序列化的 offer 标记为 `cached`。Redis 失败时可降级到进程内 TTL cache。Cache hit/miss/store/expired 在 DEBUG 日志记录。

金额模型在后端使用 `Decimal`；JSON 输出为 number 以保持前端 contract。

## Booking and verification

Split itinerary 为每张 offer 生成独立 BookingOption；option price 之和等于 itinerary total。Redirect-only options 没有 price amount。

SearchService 在有上限的进程内 registry 登记 `(search_id, itinerary_id, booking_option_id)`。Verification API 只接收这三个标识，从 registry 获取 canonical supplier、offer、previous price 与 URL。前端价格/URL 不被信任。多实例 production 需要在 Phase 14.6 替换为共享短 TTL registry。

## Frontend/backend boundary

- Frontend：地点交互、表单验证、loading/empty/error/partial states、格式化与可访问 modal。
- Backend：地点解析、矩阵、supplier 调用、normalization、价格、风险、ranking、booking binding。
- CamelCase JSON contract 来自 Pydantic alias；OpenAPI contract tests 检查 location request 与 verification request 字段。
- Production response 不包含 raw stack trace 或 raw payload。
