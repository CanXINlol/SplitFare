from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.mock_supplier import MockFlightSupplier
from app.models import SearchRequest, SearchResponse
from app.search import SearchService

app = FastAPI(title="SplitFare Mock API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
service = SearchService(MockFlightSupplier())


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/search", response_model=SearchResponse)
def search(request: SearchRequest) -> SearchResponse:
    try:
        return service.search(request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
