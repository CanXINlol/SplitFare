import { expect, test } from "@playwright/test";

test("mobile user can search and understand result trade-offs", async ({ page }) => {
  await page.goto("/");

  await page.getByLabel("Origin").fill("MEL");
  await page.getByLabel("Destination").fill("PVG");
  await page.getByLabel("Departure date").fill("2026-08-12");
  await page.getByLabel("Minimum gap").fill("3");
  await page.getByLabel("Maximum gap").fill("12");
  await page.getByRole("button", { name: /search/i }).click();

  await expect(page).toHaveURL(/\/results/);
  await expect(page.getByText("Best overall").first()).toBeVisible();
  await expect(page.getByText("Cheapest").first()).toBeVisible();
  await expect(page.getByText("Protected ticket").first()).toBeVisible();
  await expect(page.getByText(/Self-transfer warning|Risk warning/).first()).toBeVisible();
  await expect(page.getByText(/Save \$/).first()).toBeVisible();
  await expect(page.getByText(/risk/i).first()).toBeVisible();
  await expect(page.getByText("Booking options").first()).toBeVisible();
  await expect(page.getByText("Check on Trip.com").first()).toBeVisible();
  await expect(page.getByText(/Price may change at checkout/).first()).toBeVisible();
});
