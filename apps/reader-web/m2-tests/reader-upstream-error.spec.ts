import { expect, test } from "@playwright/test";

test("shows a retryable error when L2 is stopped", async ({ page }) => {
  await page.goto("/en");
  await expect(page.getByRole("heading", { name: "Content temporarily unavailable" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();
});
