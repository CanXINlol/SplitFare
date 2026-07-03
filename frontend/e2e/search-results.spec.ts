import { expect, test, type Page } from "@playwright/test";

async function searchByPlaces(page: Page, from: string, fromOption: string, to: string, toOption: string) {
  await page.goto("/");

  await page.getByRole("textbox", { name: "From" }).fill(from);
  await page.getByRole("button", { name: new RegExp(fromOption) }).first().click();
  await page.getByRole("textbox", { name: "To" }).fill(to);
  await page.getByRole("button", { name: new RegExp(toOption) }).first().click();
  await page.getByLabel("Departure date").fill("2026-08-12");
  await page.getByLabel("Minimum gap").fill("3");
  await page.getByLabel("Maximum gap").fill("12");
  await page.getByRole("button", { name: /search/i }).click();

  await expect(page).toHaveURL(/\/results/);
}

test("mobile user can search Melbourne to Shanghai and understand result trade-offs", async ({ page }) => {
  await searchByPlaces(page, "Melbourne", "Melbourne, Australia", "Shanghai", "Shanghai, China");

  await expect(page.getByText("Best overall").first()).toBeVisible();
  await expect(page.getByText("Cheapest").first()).toBeVisible();
  await expect(page.getByText("Protected ticket").first()).toBeVisible();
  await expect(page.getByText(/Melbourne \(MEL\).*Shanghai Pudong \(PVG\)|Melbourne \(MEL\).*Shanghai Hongqiao \(SHA\)/).first()).toBeVisible();
  await expect(page.getByText(/Self-transfer warning|Risk warning/).first()).toBeVisible();
  await expect(page.getByText(/Save \$/).first()).toBeVisible();
  await expect(page.getByText(/risk/i).first()).toBeVisible();
  await expect(page.getByText("Booking options").first()).toBeVisible();
  await expect(page.getByText("Check on Trip.com").first()).toBeVisible();
  await expect(page.getByText(/Price may change at checkout/).first()).toBeVisible();
  await page.getByText("Check on Trip.com").first().click();
  await expect(page.getByRole("dialog", { name: /pre-booking verification/i })).toBeVisible();
  await expect(page.getByText(/Review before leaving SplitFare|not available/i)).toBeVisible();
});

test("mobile user can search with Chinese city aliases", async ({ page }) => {
  await searchByPlaces(page, "墨尔本", "Melbourne, Australia", "上海", "Shanghai, China");

  await expect(page.getByText("Best overall").first()).toBeVisible();
  await expect(page.getByText(/Melbourne \(MEL\)/).first()).toBeVisible();
  await expect(page.getByText(/Shanghai Pudong \(PVG\)|Shanghai Hongqiao \(SHA\)/).first()).toBeVisible();
});

test("mobile user can submit direct airport inputs and see empty state", async ({ page }) => {
  await searchByPlaces(page, "PVG", "Shanghai Pudong Airport", "MEL", "Melbourne Airport");

  await expect(page.getByText("No matching mock fares")).toBeVisible();
  await expect(page.getByText("No itinerary matched this search.")).toBeVisible();
});

test("unknown place input shows a friendly validation error", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("textbox", { name: "From" }).fill("Atlantis");
  await page.getByRole("button", { name: /search/i }).click();

  await expect(page.getByText("Choose a From location")).toBeVisible();
});
