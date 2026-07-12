import { z } from "zod";
import { Cabin, RouteSort, type RouteDiscoveryRequest } from "./types";

export const searchSchema = z.object({
  originCityId: z.string().regex(/^city:[a-z0-9-]+$/, "city_required"),
  destinationCityId: z.string().regex(/^city:[a-z0-9-]+$/, "city_required"),
  departureDate: z.string().min(1, "Choose a departure date"),
  minGapHours: z.coerce.number().min(1).max(24),
  maxGapHours: z.coerce.number().min(1).max(36),
  passengers: z.coerce.number().int().min(1).max(9),
  cabin: z.nativeEnum(Cabin),
  maxResults: z.coerce.number().int().min(1).max(100).default(20),
  sort: z.nativeEnum(RouteSort).default(RouteSort.BestRoute),
}).refine((data) => data.maxGapHours >= data.minGapHours, {
  message: "Maximum gap must be at least the minimum gap",
  path: ["maxGapHours"],
}).refine((data) => data.originCityId !== data.destinationCityId, {
  message: "cities_must_differ",
  path: ["destinationCityId"],
});

export type SearchInput = RouteDiscoveryRequest;
