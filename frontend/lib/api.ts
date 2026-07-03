import type { SearchInput } from "./schema";
import type {
  PreBookingVerificationRequest,
  PreBookingVerificationResponse,
  SearchResponse,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function searchFlights(input: SearchInput, signal?: AbortSignal): Promise<SearchResponse> {
  const response = await fetch(`${API_URL}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
    signal,
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? "Search failed. Is the API running?");
  }
  return response.json() as Promise<SearchResponse>;
}

export async function verifyBookingOption(
  input: PreBookingVerificationRequest,
  signal?: AbortSignal,
): Promise<PreBookingVerificationResponse> {
  const response = await fetch(`${API_URL}/api/booking-options/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
    signal,
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? "Could not verify this booking option.");
  }
  return response.json() as Promise<PreBookingVerificationResponse>;
}
