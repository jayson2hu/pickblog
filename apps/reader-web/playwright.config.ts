import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  fullyParallel: true,
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry"
  },
  webServer:
    process.env.PLAYWRIGHT_EXTERNAL_SERVER === "1"
      ? undefined
      : {
          command: "npm --prefix D:\\vscodefile\\pickblog\\apps\\reader-web run dev -- --hostname 127.0.0.1 --port 3000",
          url: "http://127.0.0.1:3000/en",
          reuseExistingServer: process.env.CI !== "1",
          timeout: 120_000
        },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 5"] } }
  ]
});
