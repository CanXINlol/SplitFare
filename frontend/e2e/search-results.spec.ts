import { expect, test, type Page } from "@playwright/test";

async function chooseCity(page: Page, field: "From" | "To" | "出发城市" | "到达城市", continent: string, country: string, city: string) {
  await page.getByRole("button", { name: new RegExp(`^${field}:`) }).click();
  await page.getByRole("button", { name: continent, exact: true }).click();
  await page.getByRole("button", { name: new RegExp(`^${country} [A-Z]{2}$`) }).click();
  await page.getByRole("button", { name: new RegExp(`^${city}`) }).click();
}

async function search(page: Page, language: "en" | "zh" = "en") {
  await page.getByLabel(language === "en" ? "Departure" : "出发日期").fill("2026-08-12");
  await page.getByRole("button", { name: new RegExp(language === "en" ? "Discover routes" : "发现路线") }).click();
  await expect(page).toHaveURL(/\/results/);
  await expect(page.getByText(language === "en" ? "Candidate split-ticket routes" : "候选拆票路线").first()).toBeVisible();
}

test("Melbourne to Shanghai discovers airport-level split routes", async ({ page }) => {
  await page.goto("/");
  await chooseCity(page, "From", "Oceania", "Australia", "Melbourne");
  await chooseCity(page, "To", "Asia", "China", "Shanghai");
  await search(page);
  await expect(page).toHaveURL(/originCityId=city%3Amelbourne-au/);
  await expect(page).toHaveURL(/destinationCityId=city%3Ashanghai-cn/);
  await expect(page.getByText("MEL · AVV").first()).toBeVisible();
  await expect(page.getByText("PVG · SHA").first()).toBeVisible();
  const card = page.locator("article.route-card").first();
  await expect(card.getByText(/Candidate route · self-transfer/)).toBeVisible();
  await expect(card.getByText(/No flight schedule has been checked/)).toBeVisible();
  await expect(card.getByText(/Confirmed price/)).toHaveCount(0);
});

test("墨尔本到上海显示中文路线和双航段入口", async ({ page }) => {
  await page.goto("/"); await page.getByRole("button", { name: "Switch language" }).click();
  await chooseCity(page, "出发城市", "大洋洲", "澳大利亚", "墨尔本");
  await chooseCity(page, "到达城市", "亚洲", "中国", "上海");
  await search(page, "zh");
  const card = page.locator("article.route-card").first();
  await expect(card.getByText(/候选路线 · 自助中转/)).toBeVisible();
  await expect(card.getByText("系统没有检查具体航班时刻。")).toBeVisible();
  await expect(card.getByText(/第一段：/)).toBeVisible();
  await expect(card.getByText(/第二段：/)).toBeVisible();
  await expect(card.getByRole("button", { name: /Google Flights/ })).toHaveCount(3);
});

test("language switch preserves routes and manual input without rediscovery", async ({ page }) => {
  let discoveryCalls = 0;
  page.on("request", (request) => { if (request.url().endsWith("/api/routes/discover")) discoveryCalls += 1; });
  await page.goto("/"); await search(page); await expect.poll(() => discoveryCalls).toBe(1);
  const card = page.locator("article.route-card").first();
  await card.getByRole("button", { name: "Compare prices manually" }).click();
  await card.getByLabel("First-leg price").fill("420");
  await page.getByRole("button", { name: "Switch language" }).click();
  await expect(card.getByLabel("第一段价格")).toHaveValue("420");
  await expect.poll(() => discoveryCalls).toBe(1);
});

test("mobile provider reminder opens from both segment search controls", async ({ page }) => {
  await page.goto("/"); await search(page);
  const card = page.locator("article.route-card").first();
  const links = card.getByRole("button", { name: /Google Flights/ });
  await links.nth(0).click();
  await expect(page.getByRole("dialog", { name: "Google Flights" })).toBeVisible();
  await expect(page.getByText(/The provider may require you to enter these details manually/)).toBeVisible();
  await page.getByRole("button", { name: "Close" }).first().click();
  await links.nth(1).click();
  await expect(page.getByRole("dialog", { name: "Google Flights" })).toBeVisible();
});

test("manual comparison saves fees and restores after refresh", async ({ page }) => {
  await page.goto("/"); await search(page);
  let card = page.locator("article.route-card").first();
  await card.getByRole("button", { name: "Compare prices manually" }).click();
  await card.getByLabel("First-leg price").fill("420"); await card.getByLabel("Second-leg price").fill("260");
  await card.getByLabel("Baggage fee").fill("80"); await card.getByLabel("Protected ticket price").fill("920");
  await expect(card.getByText("$760")).toBeVisible();
  await expect(card.getByText("$160", { exact: true })).toBeVisible();
  await card.getByRole("button", { name: "Save comparison" }).click();
  await page.reload(); card = page.locator("article.route-card").first();
  await card.getByRole("button", { name: "Compare prices manually" }).click();
  await expect(card.getByLabel("First-leg price")).toHaveValue("420");
});
