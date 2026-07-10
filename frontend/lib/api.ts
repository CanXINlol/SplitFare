import type { SearchInput } from "./schema";
import type {
  PlaceSearchResponse,
  PreBookingVerificationRequest,
  PreBookingVerificationResponse,
  ResolvedPlace,
  SearchResponse,
} from "./types";

const configuredApiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
if (process.env.NEXT_PUBLIC_APP_ENV === "production" && !configuredApiUrl) {
  throw new Error("NEXT_PUBLIC_API_BASE_URL is required for production builds.");
}
const API_URL = (configuredApiUrl ?? "http://localhost:8000").replace(/\/$/, "");
const apiProtocol = new URL(API_URL).protocol;
if (apiProtocol !== "http:" && apiProtocol !== "https:") {
  throw new Error("NEXT_PUBLIC_API_BASE_URL must use http or https.");
}

async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(`${API_URL}${path}`, init);
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw new Error(`Could not reach SplitFare API at ${API_URL}. Check that the backend is running and CORS allows this frontend origin.`);
  }
}

async function responseError(response: Response, fallback: string): Promise<Error> {
  const body = (await response.json().catch(() => null)) as {
    detail?: string;
    error?: { message?: string };
  } | null;
  return new Error(body?.error?.message ?? body?.detail ?? fallback);
}

export async function searchFlights(input: SearchInput, signal?: AbortSignal): Promise<SearchResponse> {
  const response = await apiFetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
    signal,
  });
  if (!response.ok) {
    throw await responseError(response, "Search failed. Is the API running?");
  }
  return response.json() as Promise<SearchResponse>;
}

export async function searchPlaces(query: string, signal?: AbortSignal): Promise<PlaceSearchResponse> {
  const response = await apiFetch(`/api/places/search?q=${encodeURIComponent(query)}`, { signal });
  if (!response.ok) {
    throw await responseError(response, "Could not search places.");
  }
  return response.json() as Promise<PlaceSearchResponse>;
}

export async function resolvePlace(placeId: string, signal?: AbortSignal): Promise<ResolvedPlace> {
  const response = await apiFetch("/api/places/resolve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ placeId }),
    signal,
  });
  if (!response.ok) {
    throw await responseError(response, "Could not resolve this place.");
  }
  return response.json() as Promise<ResolvedPlace>;
}

export async function verifyBookingOption(
  input: PreBookingVerificationRequest,
  signal?: AbortSignal,
): Promise<PreBookingVerificationResponse> {
  const response = await apiFetch("/api/booking-options/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
    signal,
  });
  if (!response.ok) {
    throw await responseError(response, "Could not verify this booking option.");
  }
  return response.json() as Promise<PreBookingVerificationResponse>;
}
