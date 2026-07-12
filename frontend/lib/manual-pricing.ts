export const MANUAL_PRICE_STORAGE_KEY = "splitfare:manual-comparisons:v1";
export const MANUAL_PRICE_SCHEMA_VERSION = 1;
export const MAX_MANUAL_AMOUNT_MINOR = 100_000_000;

export interface ManualPriceEntry {
  comparisonId: string;
  itineraryId: string;
  segmentId: string;
  provider: string;
  amount: string;
  currency: string;
  baggageFee: string;
  seatFee: string;
  paymentFee: string;
  groundTransferFee: string;
  accommodationFee: string;
  otherFee: string;
  enteredAt: string;
  sourceNote: string;
}

export interface ManualComparisonRecord {
  comparisonId: string;
  itineraryId: string;
  currency: string;
  entries: ManualPriceEntry[];
  protectedTicketPrice: string;
  updatedAt: string;
}

interface StoredComparisons { version: number; records: ManualComparisonRecord[] }

export interface ComparisonTotals {
  segmentTotalMinor: number;
  feeTotalMinor: number;
  splitTotalMinor: number;
  protectedTotalMinor: number | null;
  differenceMinor: number | null;
  savingsPercent: number | null;
  decisionCode: "NO_BASELINE" | "SPLIT_CHEAPER" | "SPLIT_MORE_EXPENSIVE" | "SAME_COST" | "LIMITED_SAVINGS";
}

export function parseMoneyToMinor(value: string): number {
  const normalized = value.trim();
  if (normalized === "") return 0;
  if (!/^\d{1,7}(?:\.\d{0,2})?$/.test(normalized)) throw new Error("invalid_amount");
  const [whole, decimals = ""] = normalized.split(".");
  const minor = Number(whole) * 100 + Number(decimals.padEnd(2, "0"));
  if (!Number.isSafeInteger(minor) || minor > MAX_MANUAL_AMOUNT_MINOR) throw new Error("amount_too_large");
  return minor;
}

export function calculateComparison(record: ManualComparisonRecord): ComparisonTotals {
  if (!record.currency || record.entries.some((entry) => entry.currency !== record.currency)) {
    throw new Error("currency_mismatch");
  }
  let segmentTotalMinor = 0;
  let feeTotalMinor = 0;
  for (const entry of record.entries) {
    segmentTotalMinor += parseMoneyToMinor(entry.amount);
    feeTotalMinor += [entry.baggageFee, entry.seatFee, entry.paymentFee, entry.groundTransferFee,
      entry.accommodationFee, entry.otherFee].reduce((sum, value) => sum + parseMoneyToMinor(value), 0);
  }
  const splitTotalMinor = segmentTotalMinor + feeTotalMinor;
  const hasBaseline = record.protectedTicketPrice.trim() !== "";
  const protectedTotalMinor = hasBaseline ? parseMoneyToMinor(record.protectedTicketPrice) : null;
  const differenceMinor = protectedTotalMinor === null ? null : protectedTotalMinor - splitTotalMinor;
  const savingsPercent = protectedTotalMinor && differenceMinor !== null
    ? Math.round((differenceMinor / protectedTotalMinor) * 10_000) / 100 : null;
  let decisionCode: ComparisonTotals["decisionCode"] = "NO_BASELINE";
  if (differenceMinor !== null) {
    decisionCode = differenceMinor === 0 ? "SAME_COST"
      : differenceMinor < 0 ? "SPLIT_MORE_EXPENSIVE"
      : differenceMinor < protectedTotalMinor! * 0.1 ? "LIMITED_SAVINGS" : "SPLIT_CHEAPER";
  }
  return { segmentTotalMinor, feeTotalMinor, splitTotalMinor, protectedTotalMinor, differenceMinor, savingsPercent, decisionCode };
}

function validRecord(value: unknown): value is ManualComparisonRecord {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<ManualComparisonRecord>;
  return typeof item.comparisonId === "string" && typeof item.itineraryId === "string"
    && typeof item.currency === "string" && Array.isArray(item.entries)
    && typeof item.protectedTicketPrice === "string" && typeof item.updatedAt === "string";
}

export function loadComparisons(storage: Storage): ManualComparisonRecord[] {
  const raw = storage.getItem(MANUAL_PRICE_STORAGE_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as Partial<StoredComparisons> & { comparisons?: unknown[] };
    const records = parsed.version === 0 ? parsed.comparisons : parsed.records;
    if (!Array.isArray(records)) throw new Error("invalid_storage");
    return records.filter(validRecord);
  } catch {
    storage.removeItem(MANUAL_PRICE_STORAGE_KEY);
    return [];
  }
}

export function saveComparison(storage: Storage, record: ManualComparisonRecord): void {
  calculateComparison(record);
  const records = loadComparisons(storage).filter((item) => item.itineraryId !== record.itineraryId);
  records.push(record);
  storage.setItem(MANUAL_PRICE_STORAGE_KEY, JSON.stringify({ version: MANUAL_PRICE_SCHEMA_VERSION, records }));
}

export function deleteComparison(storage: Storage, itineraryId: string): void {
  const records = loadComparisons(storage).filter((item) => item.itineraryId !== itineraryId);
  storage.setItem(MANUAL_PRICE_STORAGE_KEY, JSON.stringify({ version: MANUAL_PRICE_SCHEMA_VERSION, records }));
}

export function clearComparisons(storage: Storage): void { storage.removeItem(MANUAL_PRICE_STORAGE_KEY); }

export function exportComparisons(storage: Storage): string {
  return JSON.stringify({ version: MANUAL_PRICE_SCHEMA_VERSION, records: loadComparisons(storage) }, null, 2);
}

export function emptyComparison(itineraryId: string, currency = "AUD"): ManualComparisonRecord {
  const comparisonId = `manual:${itineraryId}`;
  const enteredAt = new Date().toISOString();
  const entry = (segmentId: string): ManualPriceEntry => ({
    comparisonId, itineraryId, segmentId, provider: "manual", amount: "", currency,
    baggageFee: "", seatFee: "", paymentFee: "", groundTransferFee: "",
    accommodationFee: "", otherFee: "", enteredAt, sourceNote: "",
  });
  return {
    comparisonId, itineraryId, currency,
    entries: [entry(`${itineraryId}:leg-1`), entry(`${itineraryId}:leg-2`)],
    protectedTicketPrice: "", updatedAt: enteredAt,
  };
}
