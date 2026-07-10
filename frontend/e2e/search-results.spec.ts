import { expect, test, type Page } from "@playwright/test";

async function choosePlace(page: Page, field: "From" | "To", value: string, option: string) {
  await page.getByRole("combobox", { name: field }).fill(value);
  await page.getByRole("option", { name: new RegExp(option) }).first().click();
}

async function submitCurrentSearch(page: Page) {
  await page.getByLabel("Departure date").fill("2026-08-12");
  await page.getByLabel("Minimum gap").fill("3");
  await page.getByLabel("Maximum gap").fill("12");
  await page.getByRole("button", { name: /search/i }).click();

  await expect(page).toHaveURL(/\/results/);
}

test("mobile user can search Melbourne to Shanghai and understand result trade-offs", async ({ page }) => {
  await page.goto("/");
  await submitCurrentSearch(page);

  await expect(page.getByText("Best overall").first()).toBeVisible();
  await expect(page.getByText("Cheapest").first()).toBeVisible();
  await expect(page.getByText("Protected ticket").first()).toBeVisible();
  await expect(page.getByText(/Melbourne \(MEL\).*Shanghai Pudong \(PVG\)|Melbourne \(MEL\).*Shanghai Hongqiao \(SHA\)/).first()).toBeVisible();
  await expect(page.getByText(/Self-transfer warning|Risk warning/).first()).toBeVisible();
  await expect(page.getByText(/Save \$/).first()).toBeVisible();
  await expect(page.getByText(/risk/i).first()).toBeVisible();
  await expect(page.getByText("Booking options").first()).toBeVisible();
  await expect(page.getByText(/Confirmed demo price/).first()).toBeVisible();
  await expect(page.getByText("Check on Trip.com").first()).toBeVisible();
  await expect(page.getByText(/Price may change/).first()).toBeVisible();
  await page.getByText("Check on Trip.com").first().click();
  await expect(page.getByRole("dialog", { name: /review before leaving SplitFare/i })).toBeVisible();
  await expect(page.getByText(/Review before leaving SplitFare|not available/i)).toBeVisible();
});

test("mobile user can search with Chinese city aliases", async ({ page }) => {
  await page.goto("/");
  await choosePlace(page, "From", "\u58a8\u5c14\u672c", "Melbourne, Australia");
  await choosePlace(page, "To", "\u4e0a\u6d77", "Shanghai, China");
  await submitCurrentSearch(page);

  await expect(page.getByText("Best overall").first()).toBeVisible();
  await expect(page.getByText(/Melbourne \(MEL\)/).first()).toBeVisible();
  await expect(page.getByText(/Shanghai Pudong \(PVG\)|Shanghai Hongqiao \(SHA\)/).first()).toBeVisible();
});

test("mobile user can submit direct airport inputs and see empty state", async ({ page }) => {
  await page.goto("/");
  await choosePlace(page, "From", "PVG", "Shanghai Pudong Airport");
  await choosePlace(page, "To", "MEL", "Melbourne Airport");
  await submitCurrentSearch(page);

  await expect(page.getByText("No matching mock fares")).toBeVisible();
  await expect(page.getByText("No itinerary matched this search.")).toBeVisible();
});

test("unknown place input shows a friendly validation error", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("combobox", { name: "From" }).fill("Atlantis");
  await page.getByRole("button", { name: /search/i }).click();

  await expect(page.getByText("Choose a From location")).toBeVisible();
});

test("exact airport MEL to PVG searches only the selected airports", async ({ page }) => {
  await page.goto("/");
  await choosePlace(page, "From", "MEL", "Melbourne Airport");
  await choosePlace(page, "To", "PVG", "Shanghai Pudong Airport");
  await submitCurrentSearch(page);

  await expect(page.getByText("From: MEL", { exact: true })).toBeVisible();
  await expect(page.getByText("To: PVG", { exact: true })).toBeVisible();
  await expect(page.getByText(/Melbourne \(MEL\).*Shanghai Pudong \(PVG\)/).first()).toBeVisible();
});

test("protected and split-ticket results remain visibly distinct", async ({ page }) => {
  await page.goto("/");
  await submitCurrentSearch(page);
  await expect(page.getByText("Protected itinerary").first()).toBeVisible();
  await expect(page.getByText("Self-transfer - separate tickets").first()).toBeVisible();
  await expect(page.getByText("Separate tickets").first()).toBeVisible();
});

test("mock verification unchanged state is displayed", async ({ page }) => {
  await page.goto("/");
  await submitCurrentSearch(page);
  const card = page.locator("article").filter({ hasText: "MU738" }).first();
  await card.getByRole("button", { name: /Verify itinerary demo price/ }).first().click();
  await expect(page.getByRole("dialog", { name: /Review before leaving SplitFare/ })).toBeVisible();
  await expect(page.getByText(/Current verified price/)).toBeVisible();
});

test("mock verification price changed state shows before and after", async ({ page }) => {
  await page.goto("/");
  await submitCurrentSearch(page);
  const card = page.locator("article").filter({ hasText: "MU740" }).first();
  await card.getByRole("button", { name: /Verify itinerary demo price/ }).first().click();
  await expect(page.getByRole("dialog", { name: /Review before leaving SplitFare/ })).toBeVisible();
  await expect(page.getByText("Price changed")).toBeVisible();
  await expect(page.getByText(/Before:.*After:/)).toBeVisible();
});

test("mock verification unavailable state disables continuation", async ({ page }) => {
  await page.goto("/");
  await submitCurrentSearch(page);
  const card = page.locator("article").filter({ hasText: "QF129" }).first();
  await card.getByRole("button", { name: /Verify itinerary demo price/ }).first().click();
  await expect(page.getByRole("dialog", { name: /This option is not available/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "No provider link available" })).toBeDisabled();
});

test("partial supplier failure remains a non-blocking results warning", async ({ page }) => {
  await page.route("**/api/search", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    body.status = "partial";
    body.errors = [{ supplier: "DemoAir", origin: "MEL", destination: "PVG", code: "supplier_timeout", message: "DemoAir timed out." }];
    await route.fulfill({ response, json: body });
  });
  await page.goto("/");
  await submitCurrentSearch(page);
  await expect(page.getByText("Partial results")).toBeVisible();
  await expect(page.getByText("Best overall").first()).toBeVisible();
});
