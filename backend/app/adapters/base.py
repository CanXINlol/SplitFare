from abc import ABC, abstractmethod

from app.models import NormalizedFlightOffer, SearchRequest


class FlightSupplier(ABC):
    """Replaceable boundary for mock or future authorised flight suppliers."""

    @abstractmethod
    def search(self, request: SearchRequest) -> list[NormalizedFlightOffer]:
        raise NotImplementedError
