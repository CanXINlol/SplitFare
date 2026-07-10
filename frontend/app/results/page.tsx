import { Suspense } from "react";
import { ResultsView } from "@/components/results-view";

export const dynamic = "force-dynamic";

export default function ResultsPage() {
  return (
    <div>
      <Suspense fallback={<div className="page-fallback" role="status"><i /><i /><i /></div>}>
        <ResultsView />
      </Suspense>
    </div>
  );
}
