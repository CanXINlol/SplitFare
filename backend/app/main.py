from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.adapters.duffel import DuffelSupplierAdapter
from app.adapters.mock_supplier import MockSupplierAdapter
from app.adapters.orchestrator import SupplierOrchestrator
from app.adapters.skyscanner import SkyscannerSupplierAdapter
from app.adapters.trip_com import TripComAffiliateAdapter
from app.models import SearchRequest, SearchResponse
from app.models import Supplier
from app.search import SearchService
from app.search_orchestrator import SearchOrchestrator

app = FastAPI(title="SplitFare Mock API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
supplier_orchestrator = SupplierOrchestrator([
    MockSupplierAdapter(Supplier.mock_sky),
    MockSupplierAdapter(Supplier.demo_air),
    MockSupplierAdapter(Supplier.budget_demo),
    DuffelSupplierAdapter(),
    SkyscannerSupplierAdapter(),
    TripComAffiliateAdapter(),
])
service = SearchService(SearchOrchestrator(supplier_orchestrator))


def remove_raw_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: remove_raw_payload(item)
            for key, item in value.items()
            if key != "rawPayload"
        }
    if isinstance(value, list):
        return [remove_raw_payload(item) for item in value]
    return value


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest, debug: bool = False) -> JSONResponse:
    try:
        result = await service.search(request)
        payload = result.model_dump(mode="json", by_alias=True)
        return JSONResponse(payload if debug else remove_raw_payload(payload))
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
