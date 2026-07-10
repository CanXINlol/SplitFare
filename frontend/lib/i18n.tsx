"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type Locale = "zh" | "en";
type Messages = Record<string, string>;

const en: Messages = {
  "nav.product": "SplitFare",
  "nav.how": "How it works",
  "nav.safety": "Transfer safety",
  "nav.language": "中文",
  "home.eyebrow": "Protected fares vs self-transfer combinations",
  "home.title": "See the savings. Understand the trade-off.",
  "home.subtitle": "Compare a conventional protected ticket with separately booked flights through one hub. All fares in this release are deterministic demo data.",
  "home.mock": "MOCK DATA",
  "home.trust1.title": "Transparent risk",
  "home.trust1.body": "Self-transfer, baggage and connection warnings stay visible.",
  "home.trust2.title": "Airport-level search",
  "home.trust2.body": "Choose cities; SplitFare checks their supported airports.",
  "home.trust3.title": "Verify before leaving",
  "home.trust3.body": "Demo availability is checked again before any redirect.",
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
  "search.submit": "Compare itineraries",
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
  "results.searching": "Searching airport combinations",
  "results.searchingBody": "We are checking protected routes and one-stop self-transfer combinations.",
  "results.empty": "No matching itineraries",
  "results.emptyBody": "Try a wider connection window or another travel date.",
  "results.error": "Search could not be completed",
  "results.retry": "Try again",
  "results.partial": "Some supplier checks failed. Available demo results are still shown.",
  "results.mock": "Demo prices — not live availability",
  "results.count": "{count} itineraries",
  "results.baseline": "Protected baseline",
  "results.cheapest": "Cheapest",
  "results.safest": "Safest split",
  "results.best": "Best overall",
  "results.all": "All ranked options",
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
  "card.details": "Flight and purchase options",
  "card.hideDetails": "Hide details",
  "card.verify": "Verify demo price",
  "card.redirect": "Check supplier",
  "price.confirmed": "Confirmed demo price",
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
  "verify.checking": "Rechecking demo availability…",
  "verify.available": "Option available in demo data",
  "verify.unavailable": "This option is no longer available",
  "verify.unsupported": "Supplier verification is not supported",
  "verify.before": "Previous",
  "verify.now": "Current",
  "verify.unchanged": "No demo price change",
  "verify.changed": "Price changed",
  "verify.close": "Close",
  "verify.continue": "Continue to supplier",
  "verify.noRedirect": "No external booking link is configured for this demo.",
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
  "error.default": "Something went wrong. Please try again.",
  "disclaimer": "Fictional demo fares only. SplitFare does not sell tickets and does not guarantee price, baggage transfer, entry, visa or connection feasibility.",
};

const zh: Messages = {
  "nav.product": "SplitFare 拆票助手", "nav.how": "工作原理", "nav.safety": "中转风险", "nav.language": "EN",
  "home.eyebrow": "联程保护票与自组中转对比", "home.title": "看清能省多少，也看清代价。",
  "home.subtitle": "对比普通联程票和经一个中转点、分别购买的航班组合。本版本全部价格均为确定性的模拟数据。", "home.mock": "模拟数据",
  "home.trust1.title": "风险透明", "home.trust1.body": "自助中转、行李与衔接风险始终可见。",
  "home.trust2.title": "机场级搜索", "home.trust2.body": "只需选择城市，系统会搜索其支持的机场。",
  "home.trust3.title": "跳转前验价", "home.trust3.body": "离开本站前再次检查模拟价格与可用性。",
  "search.from": "出发城市", "search.to": "到达城市", "search.chooseCity": "选择城市", "search.departure": "出发日期",
  "search.passengers": "乘客", "search.cabin": "舱位", "search.minGap": "最短中转", "search.maxGap": "最长中转", "search.hours": "小时",
  "search.sort": "排序", "search.value": "综合价值", "search.cheapest": "价格最低", "search.baggage": "可能托运行李",
  "search.submit": "比较行程", "search.loading": "正在准备搜索…", "search.sameCity": "出发和到达城市不能相同。",
  "search.catalogError": "无法加载支持的城市，请检查后端 API 是否运行。",
  "city.title.from": "选择出发城市", "city.title.to": "选择到达城市", "city.close": "关闭城市选择器",
  "city.continent": "大洲", "city.country": "国家或地区", "city.city": "城市", "city.airports": "将搜索机场",
  "city.unavailable": "暂不可搜索", "city.cancel": "取消",
  "results.back": "修改搜索", "results.title": "航班组合", "results.subtitle": "按综合价值与风险排列联程票和自助中转方案。",
  "results.searching": "正在搜索机场组合", "results.searchingBody": "正在检查普通联程路线与一次中转的拆票组合。",
  "results.empty": "没有符合条件的行程", "results.emptyBody": "可尝试放宽中转时间或更换日期。",
  "results.error": "搜索未能完成", "results.retry": "重试", "results.partial": "部分供应商查询失败，以下仍展示可用的模拟结果。",
  "results.mock": "模拟价格，并非实时库存", "results.count": "共 {count} 条行程", "results.baseline": "联程基准",
  "results.cheapest": "价格最低", "results.safest": "最安全拆票", "results.best": "综合最佳", "results.all": "全部排序结果",
  "card.protected": "联程保护票", "card.split": "自助中转 · 分开出票", "card.savings": "节省 {amount}", "card.noSavings": "基准票价",
  "card.duration": "总耗时", "card.connection": "中转", "card.direct": "直飞 / 联程保护", "card.risk": "风险",
  "card.source": "价格来源", "card.baggageUnknown": "行李信息未知", "card.ticket": "第 {count} 张票", "card.flight": "航班",
  "card.checked": "检查于 {time}", "card.details": "航班与购买选项", "card.hideDetails": "收起详情",
  "card.verify": "验证模拟价格", "card.redirect": "前往供应商查看",
  "price.confirmed": "已确认模拟价格", "price.cached": "缓存价格", "price.estimated": "估算价格",
  "price.redirect_only": "前往供应商查看", "price.unavailable": "不可用", "price.change": "结账时价格可能变化",
  "risk.low": "低", "risk.medium": "中", "risk.high": "高", "risk.extreme": "极高", "risk.help": "风险评分仅用于辅助判断，不构成保证。",
  "verify.title": "继续前再次确认", "verify.checking": "正在检查模拟库存…", "verify.available": "模拟数据中仍可用",
  "verify.unavailable": "此选项已不可用", "verify.unsupported": "该供应商不支持验价", "verify.before": "之前价格", "verify.now": "当前价格",
  "verify.unchanged": "模拟价格未变化", "verify.changed": "价格已变化", "verify.close": "关闭", "verify.continue": "继续前往供应商",
  "verify.noRedirect": "此演示未配置外部购买链接。",
  "common.economy": "经济舱", "common.premium_economy": "超级经济舱", "common.business": "商务舱", "common.first": "头等舱",
  "common.minutes": "{hours}小时{minutes}分", "common.na": "暂无",
  "error.validation_error": "请检查搜索条件后重试。", "error.invalid_city_id": "该城市已不可用，请重新选择。",
  "error.rate_limited": "搜索过于频繁，请稍后重试。", "error.city_catalog_unavailable": "支持的城市列表暂不可用。",
  "error.network": "无法连接 SplitFare API，请检查后端和 API 地址。", "error.default": "出现问题，请重试。",
  "disclaimer": "仅展示虚构模拟票价。SplitFare 不售票，也不保证价格、行李直挂、入境、签证或中转可行性。",
};

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
