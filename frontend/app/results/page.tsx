import { Suspense } from "react";
import { ResultsView } from "@/components/results-view";

export const dynamic = "force-dynamic";

export default function ResultsPage() {
  return (
    <main className="mx-auto max-w-6xl px-5 pb-20">
      <Suspense fallback={<p className="py-24 text-center">Loading search...</p>}>
        <ResultsView />
      </Suspense>
    </main>
  );
}
