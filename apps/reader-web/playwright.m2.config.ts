import { defineConfig, devices } from "@playwright/test";

const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;
const launchOptions = executablePath ? { executablePath } : undefined;
const port = process.env.PLAYWRIGHT_PORT ?? "3200";

export default defineConfig({
  testDir: "./m2-tests",
  timeout: 60_000,
  fullyParallel: false,
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: "on-first-retry",
    launchOptions
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }]
});
