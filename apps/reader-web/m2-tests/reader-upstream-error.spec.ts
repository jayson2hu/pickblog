import { expect, test } from "@playwright/test";

test("shows a retryable error without demo fallback when L2 is stopped", async ({ page }) => {
  await page.goto("/en");
  await expect(page.getByRole("heading", { name: "The content service did not respond" })).toBeVisible();
  await expect(page.getByText("No demonstration articles were substituted.")).toBeVisible();
  await expect(page.getByRole("button", { name: /Retry/ })).toBeVisible();
});
