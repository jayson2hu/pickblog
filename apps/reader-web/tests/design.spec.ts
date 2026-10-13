import { expect, test } from "@playwright/test";

test("reader pages fit a narrow screen and navigation remains reachable", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  for (const path of ["/zh", "/en", "/zh/items/cp-001", "/en/library", "/zh/brief"]) {
    await page.goto(path);
    await expect(page.locator("h1")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  await page.getByText("更多", { exact: true }).click();
  await page.getByRole("link", { name: "开发者", exact: true }).click();
  await expect(page).toHaveURL(/\/zh\/developers$/);
});

test("theme persists across navigation and muted text follows the palette", async ({ page }) => {
  await page.addInitScript(() => {
    if (!localStorage.getItem("cp_theme")) localStorage.setItem("cp_theme", "light");
  });
  await page.goto("/en");
  const text = page.locator(".card-copy .text-muted").first();
  const lightColor = await text.evaluate((el) => getComputedStyle(el).color);
  await page.getByRole("button", { name: "Toggle theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  expect(await text.evaluate((el) => getComputedStyle(el).color)).not.toBe(lightColor);
  await page.getByRole("link", { name: "Saved", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.getByRole("link", { name: "Saved", exact: true })).toHaveAttribute("aria-current", "page");
});
