import { z } from "zod";
import { Cabin, SortOption, type SearchRequest } from "./types";

const booleanParam = z.preprocess(
  (value) => value === "true" ? true : value === "false" ? false : value,
  z.boolean(),
);

export const searchSchema = z.object({
  origin: z.string().trim().length(3).transform((value) => value.toUpperCase()),
  destination: z.string().trim().length(3).transform((value) => value.toUpperCase()),
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
}).refine((data) => data.maxGapHours >= data.minGapHours, {
  message: "Maximum gap must be at least the minimum gap",
  path: ["maxGapHours"],
});

export type SearchInput = SearchRequest;
