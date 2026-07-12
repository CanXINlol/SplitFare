"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type Locale = "zh" | "en";
type Messages = Record<string, string>;

const en: Messages = {
  "nav.product": "SplitFare",
  "nav.how": "How it works",
  "nav.safety": "Transfer safety",
  "nav.language": "中文",
  "nav.home": "SplitFare home", "nav.primary": "Primary navigation", "nav.switch": "Switch language",
  "home.eyebrow": "Zero-cost split-ticket route discovery",
  "home.title": "Find routes worth comparing. Check prices yourself.",
  "home.subtitle": "Discover practical self-transfer routes, then check each leg on public flight-search platforms. SplitFare does not retrieve live prices.",
  "home.mock": "ROUTE DISCOVERY · NO LIVE PRICES",
  "home.trust1.title": "Transparent risk",
  "home.trust1.body": "Self-transfer, baggage and connection warnings stay visible.",
  "home.trust2.title": "Airport-level search",
  "home.trust2.body": "Choose cities; SplitFare checks their supported airports.",
  "home.trust3.title": "Manual comparison",
  "home.trust3.body": "Open each leg on a provider and compare the prices you find manually.",
  "search.from": "From",
  "search.to": "To",
  "search.chooseCity": "Choose a city",
  "search.departure": "Departure",
  "search.passengers": "Passengers",
  "search.cabin": "Cabin",
  "search.minGap": "Minimum connection",
  "search.maxGap": "Maximum connection",
  "search.hours": "hours",
  "search.sort": "Sort",
  "search.value": "Best value",
  "search.cheapest": "Cheapest",
  "search.baggage": "I may check baggage",
  "search.submit": "Discover routes",
  "search.loading": "Preparing search…",
  "search.sameCity": "Choose two different cities.",
  "search.catalogError": "The supported city list could not be loaded. Check that the API is running.",
  "city.title.from": "Choose departure city",
  "city.title.to": "Choose destination city",
  "city.close": "Close city selector",
  "city.continent": "Continent",
  "city.country": "Country or region",
  "city.city": "City",
  "city.airports": "Airports searched",
  "city.unavailable": "Not searchable",
  "city.cancel": "Cancel",
  "results.back": "Edit search",
  "results.title": "Flight combinations",
  "results.subtitle": "Protected fares and self-transfer options, ranked by value and risk.",
  "results.searching": "Connecting to flight suppliers",
  "results.searchingBody": "We are checking protected routes and one-stop self-transfer combinations across the resolved airports.",
  "results.empty": "No matching itineraries",
  "results.emptyBody": "Try a wider connection window or another travel date.",
  "results.error": "Search could not be completed",
  "results.retry": "Try again",
  "results.partial": "Some supplier searches failed. Available results are still shown.",
  "results.supplierFailed": "Flight supplier search is temporarily unavailable.",
  "results.mock": "Demo prices — not live availability",
  "mode.mock": "Demo data", "mode.sandbox": "Duffel sandbox data", "mode.live": "Live supplier prices",
  "results.count": "{count} itineraries",
  "results.baseline": "Protected baseline",
  "results.cheapest": "Cheapest",
  "results.safest": "Safest split",
  "results.best": "Best overall",
  "results.all": "All ranked options",
  "results.ranked": "Ranked",
  "card.protected": "Protected ticket",
  "card.split": "Self-transfer · separate tickets",
  "card.savings": "Save {amount}",
  "card.noSavings": "Baseline fare",
  "card.duration": "Total duration",
  "card.connection": "Connection",
  "card.direct": "Non-stop / protected",
  "card.risk": "Risk",
  "card.source": "Price source",
  "card.baggageUnknown": "Baggage unknown",
  "card.ticket": "Ticket {count}",
  "card.flight": "Flight",
  "card.checked": "Checked {time}",
  "card.operatedBy": "Operated by {airline}",
  "card.details": "Flight and purchase options",
  "card.hideDetails": "Hide details",
  "card.verify": "Verify price",
  "card.redirect": "Check supplier",
  "price.confirmed": "Confirmed price",
  "price.cached": "Cached price",
  "price.estimated": "Estimated price",
  "price.redirect_only": "Check on supplier",
  "price.unavailable": "Unavailable",
  "price.change": "Price may change at checkout",
  "risk.low": "Low",
  "risk.medium": "Medium",
  "risk.high": "High",
  "risk.extreme": "Extreme",
  "risk.help": "Risk scores are decision aids, not a guarantee.",
  "verify.title": "Check before continuing",
  "verify.eyebrow": "Pre-booking check",
  "verify.checking": "Checking price and availability…",
  "verify.available": "The price was confirmed by the provider",
  "verify.unavailable": "This option is no longer available",
  "verify.unsupported": "Pre-redirect verification is not supported",
  "verify.unsupportedBody": "This provider does not support pre-redirect price verification. The final price is determined by the provider.",
  "verify.before": "Previous",
  "verify.now": "Current",
  "verify.unchanged": "Price unchanged",
  "verify.increased": "Price increased",
  "verify.decreased": "Price decreased",
  "verify.expired": "This price has expired",
  "verify.expiredBody": "Search again or retry verification before continuing.",
  "verify.timeout": "Verification timed out",
  "verify.timeoutBody": "No price was confirmed. You can retry the verification.",
  "verify.retry": "Retry verification",
  "verify.close": "Close",
  "verify.continue": "Continue to supplier",
  "verify.noRedirect": "This supplier does not provide a trusted external booking link for this offer.",
  "common.economy": "Economy",
  "common.premium_economy": "Premium economy",
  "common.business": "Business",
  "common.first": "First",
  "common.minutes": "{hours}h {minutes}m",
  "common.na": "Not available",
  "error.validation_error": "Check the search details and try again.",
  "error.invalid_city_id": "This city is no longer available. Choose it again.",
  "error.rate_limited": "Too many searches. Wait a moment and try again.",
  "error.city_catalog_unavailable": "The supported city list is unavailable.",
  "error.network": "Could not reach the SplitFare API. Check that the backend and API URL are available.",
  "error.SUPPLIER_TIMEOUT": "The flight supplier timed out. Please try again.",
  "error.SUPPLIER_AUTH_FAILED": "The flight supplier is not configured or authentication failed.",
  "error.SUPPLIER_RATE_LIMITED": "The flight supplier rate limit was reached. Please wait and try again.",
  "error.SUPPLIER_INVALID_RESPONSE": "The flight supplier returned incomplete data.",
  "error.SUPPLIER_UNAVAILABLE": "The flight supplier is temporarily unavailable.",
  "error.SEARCH_TIMEOUT": "The overall flight search timed out.",
  "error.default": "Something went wrong. Please try again.",
  "disclaimer": "Route discovery only. SplitFare does not retrieve prices, sell tickets or guarantee baggage transfer, entry, visa or connection feasibility.",
};

const zh: Messages = {
  "nav.product": "SplitFare 拆票助手", "nav.how": "工作原理", "nav.safety": "中转风险", "nav.language": "EN",
  "nav.home": "SplitFare 首页", "nav.primary": "主导航", "nav.switch": "切换语言",
  "home.eyebrow": "零成本拆票路线发现", "home.title": "先发现值得比较的路线，再自行查询价格。",
  "home.subtitle": "发现更现实的自助中转路线，再前往公开航班搜索平台分别查询每一段。SplitFare 不获取实时价格。", "home.mock": "路线发现 · 无实时价格",
  "home.trust1.title": "风险透明", "home.trust1.body": "自助中转、行李与衔接风险始终可见。",
  "home.trust2.title": "机场级搜索", "home.trust2.body": "只需选择城市，系统会搜索其支持的机场。",
  "home.trust3.title": "手动比价", "home.trust3.body": "分别前往平台查询每一段，并把看到的价格手动比较。",
  "search.from": "出发城市", "search.to": "到达城市", "search.chooseCity": "选择城市", "search.departure": "出发日期",
  "search.passengers": "乘客", "search.cabin": "舱位", "search.minGap": "最短中转", "search.maxGap": "最长中转", "search.hours": "小时",
  "search.sort": "排序", "search.value": "综合价值", "search.cheapest": "价格最低", "search.baggage": "可能托运行李",
  "search.submit": "发现路线", "search.loading": "正在生成路线…", "search.sameCity": "出发和到达城市不能相同。",
  "search.catalogError": "无法加载支持的城市，请检查后端 API 是否运行。",
  "city.title.from": "选择出发城市", "city.title.to": "选择到达城市", "city.close": "关闭城市选择器",
  "city.continent": "大洲", "city.country": "国家或地区", "city.city": "城市", "city.airports": "将搜索机场",
  "city.unavailable": "暂不可搜索", "city.cancel": "取消",
  "results.back": "修改搜索", "results.title": "航班组合", "results.subtitle": "按综合价值与风险排列联程票和自助中转方案。",
  "results.searching": "正在连接航班供应商", "results.searchingBody": "正在根据解析后的机场检查联程路线与一次中转的拆票组合。",
  "results.empty": "没有符合条件的行程", "results.emptyBody": "可尝试放宽中转时间或更换日期。",
  "results.error": "搜索未能完成", "results.retry": "重试", "results.partial": "部分供应商查询失败，以下仍展示可用结果。", "results.supplierFailed": "航班供应商暂时无法完成搜索。",
  "results.mock": "模拟价格，并非实时库存", "mode.mock": "模拟数据", "mode.sandbox": "Duffel Sandbox 测试数据", "mode.live": "实时供应商价格", "results.count": "共 {count} 条行程", "results.baseline": "联程基准",
  "results.cheapest": "价格最低", "results.safest": "最安全拆票", "results.best": "综合最佳", "results.all": "全部排序结果", "results.ranked": "综合排序",
  "card.protected": "联程保护票", "card.split": "自助中转 · 分开出票", "card.savings": "节省 {amount}", "card.noSavings": "基准票价",
  "card.duration": "总耗时", "card.connection": "中转", "card.direct": "直飞 / 联程保护", "card.risk": "风险",
  "card.source": "价格来源", "card.baggageUnknown": "行李信息未知", "card.ticket": "第 {count} 张票", "card.flight": "航班",
  "card.checked": "检查于 {time}", "card.operatedBy": "实际承运：{airline}", "card.details": "航班与购买选项", "card.hideDetails": "收起详情",
  "card.verify": "验证价格", "card.redirect": "前往供应商查看",
  "price.confirmed": "已确认价格", "price.cached": "缓存价格", "price.estimated": "估算价格",
  "price.redirect_only": "前往供应商查看", "price.unavailable": "不可用", "price.change": "结账时价格可能变化",
  "risk.low": "低", "risk.medium": "中", "risk.high": "高", "risk.extreme": "极高", "risk.help": "风险评分仅用于辅助判断，不构成保证。",
  "verify.title": "继续前再次确认", "verify.eyebrow": "购买前检查", "verify.checking": "正在检查价格和库存…", "verify.available": "供应商已确认当前价格",
  "verify.unavailable": "此选项已不可用", "verify.unsupported": "不支持跳转前验价", "verify.unsupportedBody": "该供应商不支持跳转前验价，最终价格以供应商页面为准。", "verify.before": "之前价格", "verify.now": "当前价格",
  "verify.unchanged": "价格未变化", "verify.increased": "价格已上涨", "verify.decreased": "价格已下降", "verify.expired": "该价格已过期", "verify.expiredBody": "请重新搜索或再次验价后继续。", "verify.timeout": "验价请求超时", "verify.timeoutBody": "当前没有确认价格，您可以重新验价。", "verify.retry": "重新验价", "verify.close": "关闭", "verify.continue": "继续前往供应商",
  "verify.noRedirect": "该供应商没有为此 Offer 提供可信的外部购买链接。",
  "common.economy": "经济舱", "common.premium_economy": "超级经济舱", "common.business": "商务舱", "common.first": "头等舱",
  "common.minutes": "{hours}小时{minutes}分", "common.na": "暂无",
  "error.validation_error": "请检查搜索条件后重试。", "error.invalid_city_id": "该城市已不可用，请重新选择。",
  "error.rate_limited": "搜索过于频繁，请稍后重试。", "error.city_catalog_unavailable": "支持的城市列表暂不可用。",
  "error.network": "无法连接 SplitFare API，请检查后端和 API 地址。", "error.SUPPLIER_TIMEOUT": "航班供应商请求超时，请重试。", "error.SUPPLIER_AUTH_FAILED": "航班供应商未配置或认证失败。", "error.SUPPLIER_RATE_LIMITED": "供应商请求频率已达上限，请稍后重试。", "error.SUPPLIER_INVALID_RESPONSE": "供应商返回了不完整的数据。", "error.SUPPLIER_UNAVAILABLE": "航班供应商暂时不可用。", "error.SEARCH_TIMEOUT": "整体航班搜索超时。", "error.default": "出现问题，请重试。",
  "disclaimer": "仅用于路线发现。SplitFare 不获取价格、不售票，也不保证行李直挂、入境、签证或中转可行性。",
};

Object.assign(en, {
  "search.bestRoute": "Best route", "search.lowestRisk": "Lowest risk", "search.shortestDetour": "Shortest detour", "search.simplestTransfer": "Simplest transfer",
  "route.discovery": "Zero-cost route discovery", "route.subtitle": "Structural route ideas ranked without live fare data.", "route.searching": "Discovering candidate routes", "route.searchingBody": "We are comparing regional hubs, airport combinations, detour and structural risk — not live flights or prices.",
  "route.empty": "No practical candidate routes", "route.emptyBody": "Try a wider suggested connection window or another city pair.", "route.count": "{count} candidate routes", "route.ranked": "Route ranking", "route.candidates": "Candidate split-ticket routes", "route.candidate": "Candidate route · self-transfer",
  "route.noLivePrices": "This version discovers potential split-ticket routes but does not retrieve live prices from booking providers.", "route.disclaimer": "Choose actual flights and verify times, baggage, immigration and total cost on the provider. Routes are structural suggestions, not verified itineraries.",
  "route.suggestedGap": "Suggested connection", "route.detour": "Geographic detour", "route.transfer": "Hub transfer", "route.tickets": "Separate orders", "route.sameAirport": "Same airport", "route.crossAirport": "Airport change", "route.separateTickets": "{count} separate tickets", "route.why": "Why this hub", "route.structuralRisk": "Structural risk", "route.scheduleRisk": "Confirm when choosing flights",
  "route.detour.low": "Low detour", "route.detour.moderate": "Moderate detour", "route.detour.high": "High detour",
  "route.reason.MAJOR_HUB": "Major international hub", "route.reason.DETOUR_LOW": "Small geographic detour", "route.reason.DETOUR_MODERATE": "Moderate geographic detour", "route.reason.DETOUR_HIGH": "Large geographic detour", "route.reason.SAME_AIRPORT_TRANSFER": "No airport change in this route", "route.reason.OVERNIGHT_OPTION_POSSIBLE": "Hub can be considered for a user-selected overnight connection",
  "route.warning.SELF_TRANSFER": "This is a self-transfer route.", "route.warning.SEPARATE_TICKETS": "The two legs must be purchased separately.", "route.warning.BAGGAGE_RECHECK_POSSIBLE": "You may need to collect and re-check baggage.", "route.warning.CROSS_AIRPORT_TRANSFER": "This route changes airports at the hub.", "route.warning.GROUND_TRANSFER_NOT_INCLUDED": "Ground-transfer time and cost are not included.", "route.warning.IMMIGRATION_UNKNOWN": "You may need to clear immigration; requirements are unknown.", "route.warning.TRANSIT_RULES_UNKNOWN": "Transit and visa rules are not assessed.", "route.warning.SCHEDULE_NOT_CHECKED": "No flight schedule has been checked.", "route.warning.VERIFY_GAP_ON_PROVIDER": "Choose flights whose connection fits the suggested range.",
  "route.firstLeg": "First leg: {origin} → {destination}", "route.secondLeg": "Second leg: {origin} → {destination}", "route.fullRoute": "Optional full-route search", "route.prefilled": "Route may be prefilled", "route.manualSearch": "Enter route manually", "route.providerReminder": "Provider search reminder", "route.providerBody": "Search {origin} → {destination} for {date}. The provider may require you to enter these details manually.", "route.providerPrice": "Check the final schedule and price on the provider. SplitFare does not read the provider page.", "route.openProvider": "Check live price on provider",
  "manual.open": "Compare prices manually", "manual.hide": "Hide price workspace", "manual.eyebrow": "User-entered prices", "manual.title": "Manual price comparison", "manual.userEntered": "These prices are entered by you and are not supplier-confirmed.", "manual.currency": "Currency", "manual.leg1": "First-leg price", "manual.leg2": "Second-leg price", "manual.baggageFee": "Baggage fee", "manual.seatFee": "Seat fee", "manual.paymentFee": "Payment fee", "manual.groundTransferFee": "Ground transfer", "manual.accommodationFee": "Accommodation", "manual.otherFee": "Other fees", "manual.sourceNote": "Source note", "manual.protectedPrice": "Protected ticket price", "manual.segmentTotal": "Flight segments", "manual.feeTotal": "Additional fees", "manual.totalCost": "Split-ticket total", "manual.savings": "Potential saving", "manual.extraCost": "Extra cost", "manual.save": "Save comparison", "manual.saved": "Saved locally", "manual.reset": "Reset comparison", "manual.clearAll": "Clear all saved comparisons", "manual.export": "Export records", "manual.error.invalid_amount": "Use a non-negative amount with up to two decimal places.", "manual.error.amount_too_large": "The amount exceeds the supported limit.", "manual.error.currency_mismatch": "All values in a comparison must use one currency.",
  "manual.decision.NO_BASELINE": "No protected-ticket price has been entered, so savings cannot be calculated.", "manual.decision.SPLIT_CHEAPER": "The entered split-ticket total is lower, but the legs remain separate orders.", "manual.decision.LIMITED_SAVINGS": "The entered saving is limited and may not justify the self-transfer risk.", "manual.decision.SPLIT_MORE_EXPENSIVE": "After the entered fees, the split-ticket route costs more.", "manual.decision.SAME_COST": "The entered totals are the same; compare protection and transfer risk.",
  "manual.riskTradeoff": "Potential saving {amount} is being compared with structural risk score {risk}/100.",
});

Object.assign(zh, {
  "search.bestRoute": "综合最佳路线", "search.lowestRisk": "风险最低", "search.shortestDetour": "绕行最少", "search.simplestTransfer": "中转最简单",
  "route.discovery": "零成本路线发现", "route.subtitle": "不使用实时票价，仅根据结构因素排列候选路线。", "route.searching": "正在发现候选路线", "route.searchingBody": "正在比较区域 Hub、机场组合、绕行程度和结构风险，不查询实时航班或价格。",
  "route.empty": "没有现实的候选路线", "route.emptyBody": "可放宽建议中转时间或更换城市。", "route.count": "共 {count} 条候选路线", "route.ranked": "路线排序", "route.candidates": "候选拆票路线", "route.candidate": "候选路线 · 自助中转",
  "route.noLivePrices": "当前版本负责发现潜在的低价拆票路线，不直接获取第三方平台实时价格。", "route.disclaimer": "请在平台自行选择实际航班，并确认时刻、行李、入境和完整费用。候选路线不是已验证行程。",
  "route.suggestedGap": "建议中转时间", "route.detour": "地理绕行", "route.transfer": "Hub 中转", "route.tickets": "独立订单", "route.sameAirport": "同一机场", "route.crossAirport": "需要换机场", "route.separateTickets": "分别购买 {count} 张票", "route.why": "推荐原因", "route.structuralRisk": "结构性风险", "route.scheduleRisk": "选择航班时确认",
  "route.detour.low": "绕行较少", "route.detour.moderate": "中等绕行", "route.detour.high": "绕行较多",
  "route.reason.MAJOR_HUB": "大型国际 Hub", "route.reason.DETOUR_LOW": "地理绕行较少", "route.reason.DETOUR_MODERATE": "地理绕行中等", "route.reason.DETOUR_HIGH": "地理绕行较多", "route.reason.SAME_AIRPORT_TRANSFER": "该路线无需更换机场", "route.reason.OVERNIGHT_OPTION_POSSIBLE": "如用户选择过夜中转，可考虑该 Hub",
  "route.warning.SELF_TRANSFER": "这是自助中转路线。", "route.warning.SEPARATE_TICKETS": "两个航段需要分别购买。", "route.warning.BAGGAGE_RECHECK_POSSIBLE": "可能需要提取并重新托运行李。", "route.warning.CROSS_AIRPORT_TRANSFER": "该路线在 Hub 需要更换机场。", "route.warning.GROUND_TRANSFER_NOT_INCLUDED": "未计入地面交通时间和费用。", "route.warning.IMMIGRATION_UNKNOWN": "可能需要入境，具体要求未知。", "route.warning.TRANSIT_RULES_UNKNOWN": "系统不判断过境或签证规则。", "route.warning.SCHEDULE_NOT_CHECKED": "系统没有检查具体航班时刻。", "route.warning.VERIFY_GAP_ON_PROVIDER": "请在平台选择符合建议中转范围的航班。",
  "route.firstLeg": "第一段：{origin} → {destination}", "route.secondLeg": "第二段：{origin} → {destination}", "route.fullRoute": "可选完整路线查询", "route.prefilled": "可能已预填路线", "route.manualSearch": "需要手动输入", "route.providerReminder": "平台查询提醒", "route.providerBody": "请查询 {date} 的 {origin} → {destination}。平台可能要求手动输入这些信息。", "route.providerPrice": "实际时刻和价格以第三方平台为准；SplitFare 不读取平台页面。", "route.openProvider": "前往平台查询实时价格",
  "manual.open": "手动比较价格", "manual.hide": "收起价格工作区", "manual.eyebrow": "用户手动输入", "manual.title": "手动价格比较", "manual.userEntered": "这些价格由你输入，并非供应商确认价格。", "manual.currency": "币种", "manual.leg1": "第一段价格", "manual.leg2": "第二段价格", "manual.baggageFee": "行李费", "manual.seatFee": "座位费", "manual.paymentFee": "支付手续费", "manual.groundTransferFee": "跨机场交通", "manual.accommodationFee": "住宿", "manual.otherFee": "其他费用", "manual.sourceNote": "价格来源备注", "manual.protectedPrice": "联程票价格", "manual.segmentTotal": "航段总价", "manual.feeTotal": "附加费用", "manual.totalCost": "拆票总成本", "manual.savings": "可能节省", "manual.extraCost": "多花金额", "manual.save": "保存比较", "manual.saved": "已保存到本地", "manual.reset": "重置比较", "manual.clearAll": "清除全部比较记录", "manual.export": "导出记录", "manual.error.invalid_amount": "请输入非负金额，最多保留两位小数。", "manual.error.amount_too_large": "金额超过当前支持的上限。", "manual.error.currency_mismatch": "同一比较中的所有金额必须使用同一币种。",
  "manual.decision.NO_BASELINE": "尚未输入联程票价格，当前无法计算节省金额。", "manual.decision.SPLIT_CHEAPER": "手动输入的拆票总成本较低，但两个航段仍是独立订单。", "manual.decision.LIMITED_SAVINGS": "节省有限，可能不值得承担自助中转风险。", "manual.decision.SPLIT_MORE_EXPENSIVE": "加入输入的附加费用后，拆票不再更便宜。", "manual.decision.SAME_COST": "输入的总成本相同，请比较联程保护和中转风险。",
  "manual.riskTradeoff": "可能节省 {amount}，对应当前结构风险评分 {risk}/100。",
});

const warningKeys: Record<string, string> = {
  "This is a self-transfer itinerary.": "warning.selfTransfer",
  "Your second ticket may not be protected if the first flight is delayed.": "warning.missedConnection",
  "The connection time is under 3 hours.": "warning.shortGap",
  "The connection time is between 3 and 5 hours.": "warning.mediumGap",
  "The connection time is between 5 and 8 hours.": "warning.longGap",
  "This itinerary has a long layover of more than 12 hours.": "warning.veryLongGap",
  "This itinerary may require an overnight layover.": "warning.overnight",
  "This itinerary may require changing airports.": "warning.crossAirport",
  "Ground transfer time and cost are not included.": "warning.groundTransfer",
  "Baggage inclusion is unknown for at least one ticket.": "warning.baggageUnknown",
  "You may need to collect and re-check baggage.": "warning.baggageRecheck",
  "The tickets are issued by different suppliers.": "warning.suppliers",
  "The itinerary uses different airlines.": "warning.airlines",
  "A low-cost carrier is included; baggage and service fees may differ.": "warning.lcc",
  "You may need to clear immigration or meet transit visa requirements.": "warning.visaUnknown",
  "A flight arrives after midnight or departs before 6am.": "warning.lateEarly",
};

Object.assign(en, {
  "warning.selfTransfer": "This is a self-transfer itinerary.", "warning.missedConnection": "A delay on the first ticket may not protect the second ticket.",
  "warning.shortGap": "Connection time is under 3 hours.", "warning.mediumGap": "Connection time is between 3 and 5 hours.",
  "warning.longGap": "Connection time is between 5 and 8 hours.", "warning.veryLongGap": "Layover is longer than 12 hours.",
  "warning.overnight": "This itinerary may require an overnight layover.", "warning.crossAirport": "This itinerary may require changing airports.",
  "warning.groundTransfer": "Ground-transfer time and cost are not included.", "warning.baggageUnknown": "Baggage inclusion is unknown for at least one ticket.",
  "warning.baggageRecheck": "You may need to collect and re-check baggage.", "warning.suppliers": "The tickets use different suppliers.",
  "warning.airlines": "The itinerary uses different airlines.", "warning.lcc": "A low-cost carrier is included; baggage and service fees may differ.",
  "warning.visaUnknown": "Immigration or transit requirements are unknown; check official sources.", "warning.lateEarly": "A flight arrives after midnight or departs before 6am.",
});
Object.assign(zh, {
  "warning.selfTransfer": "这是自助中转行程，两张票相互独立。", "warning.missedConnection": "若第一张票延误，第二张票通常不受联程保护。",
  "warning.shortGap": "中转时间少于 3 小时。", "warning.mediumGap": "中转时间为 3 至 5 小时。", "warning.longGap": "中转时间为 5 至 8 小时。",
  "warning.veryLongGap": "中转时间超过 12 小时。", "warning.overnight": "该行程可能需要过夜中转。", "warning.crossAirport": "该行程可能需要更换机场。",
  "warning.groundTransfer": "未计入地面交通时间和费用。", "warning.baggageUnknown": "至少一张票的行李信息未知。",
  "warning.baggageRecheck": "可能需要提取并重新托运行李。", "warning.suppliers": "两张票由不同供应商提供。", "warning.airlines": "两段航班使用不同航司。",
  "warning.lcc": "行程包含低成本航司，行李和服务费用可能不同。", "warning.visaUnknown": "入境或过境要求未知，请查询官方信息。",
  "warning.lateEarly": "行程包含午夜后到达或早上 6 点前出发的航班。",
});

const dictionaries = { en, zh };
const STORAGE_KEY = "splitfare:locale:v1";

type I18nValue = { locale: Locale; setLocale: (locale: Locale) => void; t: (key: string, params?: Record<string, string | number>) => string; warning: (value: string) => string };
const I18nContext = createContext<I18nValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");
  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    setLocaleState(saved === "zh" || saved === "en" ? saved : navigator.language.toLowerCase().startsWith("zh") ? "zh" : "en");
  }, []);
  useEffect(() => { document.documentElement.lang = locale === "zh" ? "zh-CN" : "en-AU"; }, [locale]);
  const setLocale = useCallback((next: Locale) => { setLocaleState(next); window.localStorage.setItem(STORAGE_KEY, next); }, []);
  const t = useCallback((key: string, params?: Record<string, string | number>) => {
    let value = dictionaries[locale][key] ?? dictionaries.en[key] ?? key;
    for (const [name, replacement] of Object.entries(params ?? {})) value = value.replaceAll(`{${name}}`, String(replacement));
    return value;
  }, [locale]);
  const warning = useCallback((value: string) => t(warningKeys[value] ?? value), [t]);
  const context = useMemo(() => ({ locale, setLocale, t, warning }), [locale, setLocale, t, warning]);
  return <I18nContext.Provider value={context}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const value = useContext(I18nContext);
  if (!value) throw new Error("useI18n must be used inside I18nProvider");
  return value;
}
