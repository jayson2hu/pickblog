import { expect, test } from "@playwright/test";

test("reads the retained M1 article through live L2 and L3 without API mocks", async ({ page }) => {
  await page.goto("/en");
  await expect(page.getByRole("heading", { name: "Public picks" })).toBeVisible();
  const article = page.getByRole("article").filter({ hasText: "AI coding agents with durable data" });
  await expect(article).toBeVisible();
  await article.getByRole("link", { name: "AI coding agents with durable data" }).click();
  await expect(page).toHaveURL(/\/en\/items\/1$/);
  await expect(page.getByRole("heading", { name: "AI coding agents with durable data" })).toBeVisible();
  await expect(page.getByText("Six-dimension scores")).toBeVisible();
  await page.goto("/zh/items/1");
  await expect(page.getByRole("heading", { name: /ZH: AI coding agents with durable data/ })).toBeVisible();
});
