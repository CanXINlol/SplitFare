from app.models import ItineraryType, NormalizedFlightOffer, RiskAssessment, RiskLevel

SELF_TRANSFER_WARNING = "This is a self-transfer itinerary."
MISSED_CONNECTION_WARNING = (
    "Your second ticket may not be protected if the first flight is delayed."
)
BAGGAGE_WARNING = "You may need to collect and re-check baggage."
VISA_WARNING = "You may need to clear immigration or meet transit visa requirements."
OVERNIGHT_WARNING = "This itinerary may require an overnight layover."
CROSS_AIRPORT_WARNING = "This itinerary may require changing airports."

LOW_COST_AIRLINES = {"D7", "AK", "FD", "JQ", "TR", "VJ", "5J"}


def assess_itinerary_risk(
    itinerary_type: ItineraryType,
    offers: list[NormalizedFlightOffer],
    layover_gap_minutes: int | None = None,
    requires_ground_transfer: bool = False,
    checked_baggage_likely_required: bool = False,
    visa_transit_requirement_unknown: bool = True,
) -> RiskAssessment:
    is_split = itinerary_type == ItineraryType.split_ticket
    score = 45 if is_split else 10
    warnings: list[str] = []

    if is_split:
        warnings.extend([SELF_TRANSFER_WARNING, MISSED_CONNECTION_WARNING])
        gap = layover_gap_minutes or 0
        if gap < 180:
            score += 35
            warnings.append("The connection time is under 3 hours.")
        elif gap <= 300:
            score += 20
            warnings.append("The connection time is between 3 and 5 hours.")
        elif gap <= 480:
            score += 10
            warnings.append("The connection time is between 5 and 8 hours.")
        if gap > 720:
            score += 8
            warnings.append("This itinerary has a long layover of more than 12 hours.")

        is_overnight = offers[1].departure_at.date() > offers[0].arrival_at.date()
        if is_overnight:
            score += 12
            warnings.append(OVERNIGHT_WARNING)

    if requires_ground_transfer:
        score += 35
        warnings.extend([
            CROSS_AIRPORT_WARNING,
            "Ground transfer time and cost are not included.",
        ])
    if any(offer.baggage_included is None for offer in offers):
        score += 10
        warnings.append("Baggage inclusion is unknown for at least one ticket.")
    if checked_baggage_likely_required:
        score += 15
        warnings.append(BAGGAGE_WARNING)
    if len({offer.supplier for offer in offers}) > 1:
        score += 10
        warnings.append("The tickets are issued by different suppliers.")
    if len({offer.airline for offer in offers}) > 1:
        score += 8
        warnings.append("The itinerary uses different airlines.")
    if any(offer.airline.upper() in LOW_COST_AIRLINES for offer in offers):
        score += 8
        warnings.append("A low-cost carrier is included; baggage and service fees may differ.")
    if visa_transit_requirement_unknown:
        score += 15
        warnings.append(VISA_WARNING)
    if any(
        offer.arrival_at.hour < 6 or offer.departure_at.hour < 6
        for offer in offers
    ):
        score += 5
        warnings.append("A flight arrives after midnight or departs before 6am.")

    score = min(score, 100)
    level = (
        RiskLevel.low if score <= 25
        else RiskLevel.medium if score <= 55
        else RiskLevel.high if score <= 80
        else RiskLevel.extreme
    )
    return RiskAssessment(score=score, level=level, warnings=warnings)


def assess_split_risk(
    gap_minutes: int,
    offers: list[NormalizedFlightOffer],
    requires_ground_transfer: bool = False,
) -> RiskAssessment:
    """Compatibility wrapper for callers outside the matching engine."""
    return assess_itinerary_risk(
        ItineraryType.split_ticket,
        offers,
        layover_gap_minutes=gap_minutes,
        requires_ground_transfer=requires_ground_transfer,
    )
