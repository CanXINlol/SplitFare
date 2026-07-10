"use client";

import Link from "next/link";
import { useI18n } from "@/lib/i18n";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { locale, setLocale, t } = useI18n();
  return <div className="app-shell">
    <header className="topbar">
      <Link href="/" className="brand" aria-label={t("nav.home")}><span className="brand-mark">S</span><span>{t("nav.product")}</span></Link>
      <nav aria-label={t("nav.primary")}>
        <Link href="/#how">{t("nav.how")}</Link><Link href="/#safety">{t("nav.safety")}</Link>
        <button className="language-switch" type="button" onClick={() => setLocale(locale === "en" ? "zh" : "en")} aria-label={t("nav.switch")}>{t("nav.language")}</button>
      </nav>
    </header>
    <main>{children}</main>
    <footer><span className="brand-mini">SplitFare RC</span><p>{t("disclaimer")}</p></footer>
  </div>;
}
