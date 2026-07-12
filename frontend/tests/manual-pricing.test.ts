import { beforeEach, describe, expect, it } from "vitest";
import {
  MANUAL_PRICE_STORAGE_KEY, calculateComparison, clearComparisons, deleteComparison,
  emptyComparison, exportComparisons, loadComparisons, parseMoneyToMinor, saveComparison,
} from "@/lib/manual-pricing";

function record() {
  const value = emptyComparison("route:test");
  value.entries[0].amount = "420.00"; value.entries[1].amount = "260.00";
  return value;
}

describe("manual pricing", () => {
  beforeEach(() => localStorage.clear());

  it("adds two segment prices in minor units", () => expect(calculateComparison(record()).segmentTotalMinor).toBe(68_000));
  it("adds all fee categories", () => {
    const value = record(); Object.assign(value.entries[0], { baggageFee: "80", seatFee: "10", paymentFee: "5", groundTransferFee: "25", accommodationFee: "100", otherFee: "2.50" });
    expect(calculateComparison(value).feeTotalMinor).toBe(22_250);
  });
  it("compares with a protected ticket", () => { const value = record(); value.protectedTicketPrice = "920"; expect(calculateComparison(value).differenceMinor).toBe(24_000); });
  it("identifies a cheaper split route", () => { const value = record(); value.protectedTicketPrice = "920"; expect(calculateComparison(value).decisionCode).toBe("SPLIT_CHEAPER"); });
  it("identifies a more expensive split route", () => { const value = record(); value.protectedTicketPrice = "600"; expect(calculateComparison(value).decisionCode).toBe("SPLIT_MORE_EXPENSIVE"); });
  it("identifies equal prices", () => { const value = record(); value.protectedTicketPrice = "680"; expect(calculateComparison(value).decisionCode).toBe("SAME_COST"); });
  it("does not invent a baseline", () => { const totals = calculateComparison(record()); expect(totals.differenceMinor).toBeNull(); expect(totals.decisionCode).toBe("NO_BASELINE"); });
  it("rejects mixed currencies", () => { const value = record(); value.entries[1].currency = "USD"; expect(() => calculateComparison(value)).toThrow("currency_mismatch"); });
  it("rejects negative values", () => expect(() => parseMoneyToMinor("-1")).toThrow("invalid_amount"));
  it("limits very large values", () => expect(() => parseMoneyToMinor("1000001")).toThrow("amount_too_large"));
  it("preserves two-decimal precision", () => expect(parseMoneyToMinor("12.34")).toBe(1234));
  it("saves, modifies and reloads records", () => { const value = record(); saveComparison(localStorage, value); value.entries[0].amount = "500"; saveComparison(localStorage, value); expect(loadComparisons(localStorage)[0].entries[0].amount).toBe("500"); });
  it("deletes one record", () => { saveComparison(localStorage, record()); deleteComparison(localStorage, "route:test"); expect(loadComparisons(localStorage)).toEqual([]); });
  it("clears all records", () => { saveComparison(localStorage, record()); clearComparisons(localStorage); expect(loadComparisons(localStorage)).toEqual([]); });
  it("migrates version zero records", () => { localStorage.setItem(MANUAL_PRICE_STORAGE_KEY, JSON.stringify({ version: 0, comparisons: [record()] })); expect(loadComparisons(localStorage)).toHaveLength(1); });
  it("recovers safely from corrupted storage", () => { localStorage.setItem(MANUAL_PRICE_STORAGE_KEY, "{"); expect(loadComparisons(localStorage)).toEqual([]); expect(localStorage.getItem(MANUAL_PRICE_STORAGE_KEY)).toBeNull(); });
  it("exports versioned JSON", () => { saveComparison(localStorage, record()); expect(JSON.parse(exportComparisons(localStorage))).toMatchObject({ version: 1 }); });
});
