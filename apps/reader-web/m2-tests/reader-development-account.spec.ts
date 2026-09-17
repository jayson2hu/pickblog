import { expect, test } from "@playwright/test";

type Quota = { used: number; limit: number; unlimited: boolean };
type Bookmark = { content_id: string; note?: string | null };

test("persists a local development identity, bookmark, and companion usage without API mocks", async ({ page }) => {
  const email = `codepick-reader-${Date.now()}@example.com`;

  await page.goto("/en/login");
  const origin = new URL(page.url()).origin;
  await page.getByLabel("Email").fill(email);
  const loginResponsePromise = page.waitForResponse((response) => (
    new URL(response.url()).pathname === "/api/auth/login"
    && response.request().method() === "POST"
  ));
  await page.getByRole("button", { name: "Continue" }).click();
  const loginResponse = await loginResponsePromise;
  expect(loginResponse.status()).toBe(200);
  expect(new URL(loginResponse.url()).origin).toBe(origin);
  expect(loginResponse.url()).not.toContain("127.0.0.1:8000");
  await expect(page.getByText("Signed in", { exact: true })).toBeVisible();

  const token = await page.evaluate(() => localStorage.getItem("codepick_token"));
  expect(token).toBeTruthy();
  expect(token).not.toMatch(/^demo\./);
  const headers = { Authorization: `Bearer ${token}` };

  const profileResponse = await page.request.get(`${origin}/api/me`, { headers });
  expect(profileResponse.status()).toBe(200);
  expect((await profileResponse.json()).email).toBe(email);

  const quotaBeforeResponse = await page.request.get(`${origin}/api/companion/quota`, { headers });
  expect(quotaBeforeResponse.status()).toBe(200);
  const quotaBefore = await quotaBeforeResponse.json() as Quota;
  expect(quotaBefore.unlimited).toBe(false);
  expect(quotaBefore.used).toBe(0);

  await page.goto("/en/items/6");
  const bookmarkResponsePromise = page.waitForResponse((response) => (
    new URL(response.url()).pathname === "/api/bookmarks"
    && response.request().method() === "POST"
  ));
  await page.getByRole("button", { name: "Save to account" }).click();
  const bookmarkResponse = await bookmarkResponsePromise;
  expect(bookmarkResponse.status()).toBe(200);
  expect(new URL(bookmarkResponse.url()).origin).toBe(origin);
  await expect(page.getByText("Saved to your account.", { exact: true })).toBeVisible();

  await page.reload();
  await expect(page.getByLabel("Account menu")).toBeVisible();
  const bookmarksResponse = await page.request.get(`${origin}/api/bookmarks`, { headers });
  expect(bookmarksResponse.status()).toBe(200);
  const bookmarks = (await bookmarksResponse.json()).items as Bookmark[];
  expect(bookmarks).toEqual(expect.arrayContaining([
    expect.objectContaining({ content_id: "6", note: "saved from reader" })
  ]));

  const companion = page.locator("section").filter({
    has: page.getByRole("heading", { name: "Reading companion" })
  });
  await expect(companion.getByText(`${quotaBefore.limit - quotaBefore.used}/${quotaBefore.limit}`, { exact: true })).toBeVisible();
  await companion.getByLabel("Companion question").fill("context");
  const companionResponsePromise = page.waitForResponse((response) => (
    new URL(response.url()).pathname === "/api/companion"
    && response.request().method() === "POST"
  ));
  await companion.getByRole("button", { name: "Ask" }).click();
  const companionResponse = await companionResponsePromise;
  expect(companionResponse.status()).toBe(200);
  expect(new URL(companionResponse.url()).origin).toBe(origin);
  await expect(companion.getByText(/Extractive reading aid/)).toBeVisible();

  const quotaAfterResponse = await page.request.get(`${origin}/api/companion/quota`, { headers });
  expect(quotaAfterResponse.status()).toBe(200);
  const quotaAfter = await quotaAfterResponse.json() as Quota;
  expect(quotaAfter.used).toBe(quotaBefore.used + 1);
  await expect(companion.getByText(`${quotaAfter.limit - quotaAfter.used}/${quotaAfter.limit}`, { exact: true })).toBeVisible();
});
