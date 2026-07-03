import { z } from "zod";
import { Cabin, SortOption, type SearchRequest } from "./types";

const booleanParam = z.preprocess(
  (value) => value === "true" ? true : value === "false" ? false : value,
  z.boolean(),
);

export const searchSchema = z.object({
  originPlaceId: z.string().trim().min(1, "Choose a From location"),
  destinationPlaceId: z.string().trim().min(1, "Choose a To location"),
  departureDate: z.string().min(1, "Choose a departure date"),
  minGapHours: z.coerce.number().min(1).max(24),
  maxGapHours: z.coerce.number().min(1).max(36),
  passengers: z.coerce.number().int().min(1).max(9),
  cabin: z.nativeEnum(Cabin),
  maxResults: z.coerce.number().int().min(1).max(100).default(20),
  sort: z.nativeEnum(SortOption).default(SortOption.Value),
  checkedBaggageLikelyRequired: booleanParam.default(false),
  visaTransitRequirementUnknown: booleanParam.default(true),
  currency: z.string().regex(/^[A-Z]{3}$/).default("AUD"),
  promoCodeNote: z.string().trim().max(240).optional().nullable(),
  memberPriceNote: z.string().trim().max(240).optional().nullable(),
}).refine((data) => data.maxGapHours >= data.minGapHours, {
  message: "Maximum gap must be at least the minimum gap",
  path: ["maxGapHours"],
}).refine((data) => data.originPlaceId !== data.destinationPlaceId, {
  message: "From and To must be different",
  path: ["destinationPlaceId"],
});

export type SearchInput = SearchRequest;
