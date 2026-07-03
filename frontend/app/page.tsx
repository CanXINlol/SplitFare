import { SearchForm } from "@/components/search-form";

export default function Home() {
  return (
    <main className="mx-auto max-w-6xl px-5 pb-16 pt-10 lg:pt-20">
      <p className="mb-4 font-mono text-xs font-bold uppercase tracking-[.25em] text-coral">Split smarter - understand the trade-off</p>
      <h1 className="max-w-3xl text-5xl font-black leading-[.95] tracking-tight md:text-7xl">Two tickets can cost less.<br /><span className="text-ink/40">The risk should not be hidden.</span></h1>
      <p className="mb-10 mt-7 max-w-2xl text-lg leading-8 text-ink/70">Compare protected and self-transfer options for Melbourne to Shanghai using fictional, repeatable data.</p>
      <SearchForm />
      <p className="mt-4 text-xs text-ink/55">Demo only - no live fares, booking, payment or travel-feasibility guarantee.</p>
    </main>
  );
}
