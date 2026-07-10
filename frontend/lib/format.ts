import type { Locale } from "./i18n";

const localeTag = (locale: Locale) => locale === "zh" ? "zh-CN" : "en-AU";

export const formatMoney = (amount: number, currency: string, locale: Locale) =>
  new Intl.NumberFormat(localeTag(locale), { style: "currency", currency, maximumFractionDigits: 0 }).format(amount);

export const formatDateTime = (value: string, locale: Locale) =>
  new Intl.DateTimeFormat(localeTag(locale), { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));

export const formatTime = (value: string, locale: Locale) =>
  new Intl.DateTimeFormat(localeTag(locale), { hour: "2-digit", minute: "2-digit" }).format(new Date(value));
