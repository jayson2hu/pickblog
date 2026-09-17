import { expect, test } from "@playwright/test";

test("reads, verifies, and saves a public-source article without API mocks", async ({ page }) => {
  const title = "How we make AI coding more cost efficient without sacrificing task quality";

  await page.goto("/en");
  await expect(page.getByRole("heading", { name: "Public picks" })).toBeVisible();
  const article = page.getByRole("article").filter({ hasText: title });
  await expect(article).toBeVisible();
  await expect(article.getByText("Public source")).toBeVisible();
  await expect(article.getByText("Rule analysis")).toBeVisible();
  await expect(article.getByText("Not human reviewed")).toBeVisible();
  await expect(article.getByRole("link", { name: "github.blog" })).toHaveAttribute("href", /^https:\/\/github\.blog\//);
  await article.getByRole("button", { name: "Save for later" }).click();
  await expect(article.getByRole("button", { name: "Saved locally" })).toBeVisible();

  await page.reload();
  await expect(page.getByRole("article").filter({ hasText: title }).getByRole("button", { name: "Saved locally" })).toBeVisible();
  await page.goto("/en/library");
  await expect(page.getByRole("heading", { name: "Saved reading" })).toBeVisible();
  await expect(page.getByRole("article").getByRole("heading", { name: title })).toBeVisible();
  await expect(page.getByRole("article").getByRole("link", { name: "Open source" })).toHaveAttribute("href", /^https:\/\/github\.blog\//);
  await page.getByRole("article").getByRole("link", { name: "View analysis" }).click();
  await expect(page).toHaveURL(/\/en\/items\/6$/);
  await expect(page.getByRole("heading", { name: title })).toBeVisible();
  await expect(page.getByText("Rule-based ordering")).toBeVisible();
  await expect(page.getByText("Six-dimension scores")).toHaveCount(0);
  await expect(page.getByLabel("Content provenance").getByText("Not human reviewed")).toBeVisible();
  await expect(page.getByRole("link", { name: "Open publisher source" })).toHaveAttribute("href", /^https:\/\/github\.blog\//);

  await page.goto("/zh/items/6");
  await expect(page.getByRole("heading", { name: title })).toBeVisible();
  await expect(page.getByText("暂无译文")).toBeVisible();
  await expect(page.getByText("规则排序")).toBeVisible();
  await expect(page.getByText("六维评分")).toHaveCount(0);
});
