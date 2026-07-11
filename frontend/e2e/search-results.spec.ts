import { expect, test, type Page } from "@playwright/test";

async function chooseCity(page: Page, field: "From" | "To" | "出发城市" | "到达城市", continent: string, country: string, city: string) {
  await page.getByRole("button", { name: new RegExp(`^${field}:`) }).click();
  await page.getByRole("button", { name: continent, exact: true }).click();
  await page.getByRole("button", { name: new RegExp(`^${country} [A-Z]{2}$`) }).click();
  await page.getByRole("button", { name: new RegExp(`^${city}`) }).click();
}

async function search(page: Page, language: "en" | "zh" = "en") {
  await page.getByLabel(language === "en" ? "Departure" : "出发日期").fill("2026-08-12");
  await page.getByRole("button", { name: new RegExp(language === "en" ? "Compare itineraries" : "比较行程") }).click();
  await expect(page).toHaveURL(/\/results/);
  await expect(page.getByText(language === "en" ? "Best overall" : "综合最佳").first()).toBeVisible();
}

test("Melbourne to Shanghai uses structured city ids and airport matrix", async ({ page }) => {
  await page.goto("/");
  await chooseCity(page, "From", "Oceania", "Australia", "Melbourne");
  await chooseCity(page, "To", "Asia", "China", "Shanghai");
  await search(page);
  await expect(page).toHaveURL(/originCityId=city%3Amelbourne-au/);
  await expect(page).toHaveURL(/destinationCityId=city%3Ashanghai-cn/);
  await expect(page.getByText("MEL · AVV").first()).toBeVisible();
  await expect(page.getByText("PVG · SHA").first()).toBeVisible();
  await expect(page.getByText(/Self-transfer · separate tickets/).first()).toBeVisible();
  await expect(page.getByText(/A delay on the first ticket may not protect/).first()).toBeVisible();
});

test("墨尔本到上海 supports complete Chinese experience", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Switch language" }).click();
  await chooseCity(page, "出发城市", "大洋洲", "澳大利亚", "墨尔本");
  await chooseCity(page, "到达城市", "亚洲", "中国", "上海");
  await search(page, "zh");
  await expect(page.getByText(/自助中转 · 分开出票/).first()).toBeVisible();
  await expect(page.getByText(/若第一张票延误/).first()).toBeVisible();
  await expect(page.getByText("模拟数据").first()).toBeVisible();
  const directCard = page.locator("article.protected-card").first();
  await directCard.getByRole("button", { name: "航班与购买选项" }).click();
  await directCard.getByRole("button", { name: /MockSky/ }).first().click();
  await expect(page.getByRole("dialog", { name: "继续前再次确认" })).toBeVisible();
  await expect(page.getByText("价格未变化").first()).toBeVisible();
});

test("language switch preserves selected cities and does not repeat flight search", async ({ page }) => {
  let searchCalls = 0;
  page.on("request", (request) => { if (request.url().endsWith("/api/search")) searchCalls += 1; });
  await page.goto("/");
  await search(page);
  await expect.poll(() => searchCalls).toBe(1);
  await page.getByRole("button", { name: "Switch language" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "墨尔本 → 上海" })).toBeVisible();
  await expect.poll(() => searchCalls).toBe(1);
});

test("verification modal shows unchanged and unavailable demo states", async ({ page }) => {
  await page.goto("/");
  await search(page);
  const directCard = page.locator("article.protected-card").first();
  await directCard.getByRole("button", { name: "Flight and purchase options" }).click();
  await expect(directCard.getByText("MU738")).toBeVisible();
  await directCard.getByRole("button", { name: /MockSky/ }).first().click();
  await expect(page.getByRole("dialog", { name: "Check before continuing" })).toBeVisible();
  await expect(page.getByText("Price unchanged").first()).toBeVisible();
});

test("partial supplier failure is non-blocking", async ({ page }) => {
  await page.route("**/api/search", async (route) => {
    const response = await route.fetch(); const body = await response.json();
    body.status = "partial"; body.errors = [{ supplier: "DemoAir", origin: "MEL", destination: "PVG", code: "SUPPLIER_TIMEOUT", message: "redacted" }];
    await route.fulfill({ response, json: body });
  });
  await page.goto("/"); await search(page);
  await expect(page.getByText(/Some supplier searches failed/)).toBeVisible();
  await expect(page.getByText("Best overall").first()).toBeVisible();
});
