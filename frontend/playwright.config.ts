import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL: "http://127.0.0.1:3010",
    trace: "on-first-retry",
  },
  webServer: [
    {
      command: "powershell -NoProfile -Command \"$env:NEXT_PUBLIC_API_URL='http://127.0.0.1:8010'; npm run dev -- --hostname 127.0.0.1 --port 3010\"",
      url: "http://127.0.0.1:3010",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "cd ../backend && .\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010",
      url: "http://127.0.0.1:8010/health",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
  projects: [
    {
      name: "mobile-chromium",
      use: {
        ...devices["iPhone 12"],
        browserName: "chromium",
        viewport: { width: 375, height: 812 },
      },
    },
  ],
});
