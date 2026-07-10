"use client";

import { SearchForm } from "@/components/search-form";
import { useI18n } from "@/lib/i18n";

export default function HomePage() {
  const { t } = useI18n();
  return <>
    <section className="hero">
      <div className="hero-copy"><span className="eyebrow">{t("home.eyebrow")}</span><h1>{t("home.title")}</h1><p>{t("home.subtitle")}</p><span className="mock-chip">● {t("home.mock")}</span></div>
      <SearchForm />
    </section>
    <section className="trust-grid" id="how">
      {[1,2,3].map((number) => <article key={number}><span>0{number}</span><h2>{t(`home.trust${number}.title`)}</h2><p>{t(`home.trust${number}.body`)}</p></article>)}
    </section>
    <section id="safety" className="safety-band"><div><span className="eyebrow">SELF-TRANSFER</span><h2>{t("risk.help")}</h2></div><p>{t("disclaimer")}</p></section>
  </>;
}
