import { expect, test } from "@playwright/test";

test("preserves stored FakeLLM scoring and translation without API mocks", async ({ page }) => {
  const sourceTitle = "AI coding agents with durable data";

  await page.goto("/en");
  const article = page.getByRole("article").filter({ hasText: sourceTitle });
  await expect(article).toBeVisible();
  await expect(article.getByLabel("Content provenance").getByText("Source unverified")).toBeVisible();
  await expect(article.getByText("Simulated scoring")).toBeVisible();
  await article.getByRole("link", { name: sourceTitle }).click();
  await expect(page).toHaveURL(/\/en\/items\/1$/);
  await expect(page.getByRole("heading", { name: sourceTitle })).toBeVisible();
  await expect(page.getByText("Six-dimension scores")).toBeVisible();
  await expect(page.getByText("Simulated scoring for tests")).toBeVisible();

  await page.goto("/zh/items/1");
  await expect(page.getByText("暂无译文")).toHaveCount(0);
  await expect(page.getByRole("group", { name: "摘录语言" })).toBeVisible();
  await expect(page.getByText("六维评分")).toBeVisible();
  await expect(page.getByText("模拟评分，仅供测试")).toBeVisible();
});
