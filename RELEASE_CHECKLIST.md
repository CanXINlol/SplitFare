# SplitFare Release Checklist — Phase 14.6

只有所有 release gate 均通过时才能标记 READY FOR RELEASE GATE。

## Product alignment

- [x] 产品比较 protected 与 split-ticket，不宣称全网最低。
- [x] Self-transfer、独立订单、延误保护、行李与 visa unknown 显著显示。
- [x] Redirect-only provider 不生成价格、不参与 ranking。
- [x] Mock price、mock verification 与 Demo Data 可识别。
- [x] 无支付、出票、登录、提醒或未授权抓取。

## Location and matrix

- [x] 城市选择只提交稳定 `city_id`；用户不能直接选择机场。
- [x] 大洲 → 国家/地区 → 城市层级来自唯一后端目录。
- [x] 旧 Place autocomplete、alias、search/resolve API 已删除。
- [x] 中文/英文覆盖首页、选择器、结果、风险、价格、错误与验价。
- [x] 语言持久化且切换语言不触发航班重搜。
- [x] 浏览器搜索状态和 flight cache 已升级到 v2。
- [x] 城市选择器支持分层切换、触屏、键盘按钮、Escape 和移动端滚动。
- [x] Melbourne → Shanghai 生成 MEL/AVV × PVG/SHA baseline。
- [x] Origin/destination/hub、route query、supplier query 与并发均有上限。
- [x] Truncation 通过 SearchResponse metadata 解释。
- [x] Overnight second-leg operational dates 不改变单一用户 departure date 产品范围。

## Algorithm and risk

- [x] Timezone-aware datetime、跨时区、跨日、DST 与 gap boundary 有测试。
- [x] Protected/split 严格区分；currency mismatch 拒绝；无 baseline savings=null。
- [x] Dedup、stable ranking、max results 与 extreme-risk demotion 有测试。
- [x] Matcher 按 second-leg origin 建索引，并由 matrix caps 防止组合爆炸。
- [x] Risk score/level 只有后端来源，0–100 clamp，split 至少 medium。

## Supplier, price, booking

- [x] Orchestrator 只调用 `supports_search=true` adapters。
- [x] Supplier timeout/partial/invalid response 不导致整体 500。
- [x] Supplier errors 清理 token/header，raw payload 默认不出后端。
- [x] `PriceStatus` 是唯一价格状态 enum。
- [x] Cache hit offer 标记 cached；过期价格不保持 confirmed。
- [x] Split booking options 按 ticket/offer 绑定，价格之和等于 itinerary total。
- [x] Verification request 只提交 search/itinerary/option IDs。
- [x] Server canonical option 防止 price/URL 注入和 option 错绑。
- [x] 外部 booking URL 只允许 HTTP(S)，非本地 HTTP 被拒绝。

## Mock / production isolation

- [x] Backend production image 默认 `ENABLE_MOCK_SUPPLIER=false`。
- [x] Production demo 必须显式启用 mock，并显示 Demo Data。
- [x] Mock mode 强制禁用 Duffel live search，防止混排。
- [x] Production CORS wildcard 启动失败。
- [x] Production debug/raw payload 与 raw exception 被屏蔽。
- [x] Production code response 无 example booking host。
- [x] Frontend production Docker build 要求显式 API base URL。

## Automated release gates

- [x] Backend Ruff：`.\.venv\Scripts\python.exe -m ruff check app tests`
- [x] Backend pytest：148 passed；禁用无收益的 pytest cache 后无 ACL warning。
- [x] Frontend typecheck：`npm run typecheck`
- [x] Frontend ESLint：`npm run lint`
- [x] Frontend Vitest：7 passed。
- [x] Playwright mobile Chromium：5 passed。
- [x] Frontend production build 完整通过。
- [x] Backend 与 frontend Docker images 构建通过。
- [x] Docker Compose startup、前端 HTTP 200 与 `/health` smoke test 通过。
- [x] 旧 `.next`、`tsconfig.tsbuildinfo`、`.pytest_cache` 与 pytest 临时缓存已清理。

## Deployment gate

- [ ] 设置 production `NEXT_PUBLIC_API_BASE_URL`。
- [ ] 设置明确 `FRONTEND_ORIGIN`，无 wildcard。
- [ ] 明确选择 production demo 或 production live。
- [ ] 如使用 PostgreSQL，运行 Alembic migration 与 seed。
- [ ] 如为多实例部署，实现共享 verification registry 与 rate limiter，或限制为单实例 demo。
- [ ] 执行部署后 health、CORS、raw payload、rate limit、mock/live 与 redirect smoke tests。

## Rollback

- [ ] 保存上一 working image/tag。
- [ ] 记录数据库 migration rollback/forward strategy。
- [ ] Supplier 故障不得通过静默 mock fallback 掩盖。
