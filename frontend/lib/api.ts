import type { SearchInput } from "./schema";
import type {
  CityCatalog,
  PreBookingVerificationRequest,
  PreBookingVerificationResponse,
  SearchResponse,
} from "./types";

const configuredApiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
if (process.env.NEXT_PUBLIC_APP_ENV === "production" && !configuredApiUrl) {
  throw new Error("NEXT_PUBLIC_API_BASE_URL is required for production builds.");
}
const API_URL = (configuredApiUrl ?? "http://localhost:8000").replace(/\/$/, "");
const searchRequestCache = new Map<string, Promise<SearchResponse>>();
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
    throw new Error("network");
  }
}

async function responseError(response: Response, fallback: string): Promise<Error> {
  const body = (await response.json().catch(() => null)) as {
    detail?: string;
    error?: { code?: string; message?: string };
  } | null;
  return new Error(body?.error?.code ?? body?.detail ?? fallback);
}

export async function searchFlights(input: SearchInput, signal?: AbortSignal): Promise<SearchResponse> {
  const key = JSON.stringify(input);
  let request = searchRequestCache.get(key);
  if (!request) {
    request = apiFetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: key,
    }).then(async (response) => {
      if (!response.ok) throw await responseError(response, "search_failed");
      return response.json() as Promise<SearchResponse>;
    }).catch((error: unknown) => {
      searchRequestCache.delete(key);
      throw error;
    });
    searchRequestCache.set(key, request);
    if (searchRequestCache.size > 12) searchRequestCache.delete(searchRequestCache.keys().next().value!);
  }
  const result = await request;
  if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
  return result;
}

export async function getCityCatalog(signal?: AbortSignal): Promise<CityCatalog> {
  const response = await apiFetch("/api/cities", { signal });
  if (!response.ok) {
    throw await responseError(response, "city_catalog_unavailable");
  }
  return response.json() as Promise<CityCatalog>;
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
