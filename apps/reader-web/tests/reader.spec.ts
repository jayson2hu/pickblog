import { expect, test } from "@playwright/test";

test("redirects the root to the default Chinese reader", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/zh$/);
  await expect(page.getByRole("heading", { name: "公共精选" })).toBeVisible();
  const homeLink = page.getByRole("navigation", { name: "主导航" }).getByRole("link", { name: "今日精选" });
  await expect(homeLink).toHaveCSS("white-space", "nowrap");
  const homeLinkBox = await homeLink.boundingBox();
  expect(homeLinkBox?.width).toBeGreaterThan(48);
  expect(homeLinkBox?.height).toBeLessThanOrEqual(52);
});

test("returns a real not-found page for an unsupported locale", async ({ page }) => {
  const response = await page.goto("/fr");
  expect(response?.status()).toBe(404);
  await expect(page.locator("body")).toContainText(/404|This page could not be found/);
});

test("renders public picks and language switch", async ({ page }) => {
  await page.goto("/en");
  await expect(page).toHaveTitle(/CodePick/);
  await expect(page.getByRole("heading", { name: "Public picks" })).toBeVisible();
  await expect(page.getByRole("article").getByText("Async Python agents are getting cheaper to operate")).toBeVisible();
  await expect(page.getByText("Fixture").first()).toBeVisible();
  await expect(page.getByText("Simulated scoring").first()).toBeVisible();
  await page.getByRole("link", { name: "中文" }).click();
  await expect(page.getByRole("heading", { name: "公共精选" })).toBeVisible();
});

test("searches the demo feed and shows an honest empty state", async ({ page }) => {
  await page.goto("/en");
  await page.getByRole("search").getByRole("searchbox").fill("no-such-reader-item");
  await page.getByRole("search").getByRole("button", { name: "Search" }).click();
  await expect(page).toHaveURL(/q=no-such-reader-item/);
  await expect(page.getByRole("heading", { name: "No public picks match this view." })).toBeVisible();
  await expect(page.getByRole("link", { name: "Reset view" })).toBeVisible();
});

test("saves a traceable local item, revisits it, and removes it", async ({ page }) => {
  await page.goto("/en");
  const article = page.getByRole("article").filter({ hasText: "Async Python agents are getting cheaper to operate" });
  await article.getByRole("button", { name: "Save for later" }).click();
  await expect(article.getByRole("button", { name: "Saved locally" })).toBeVisible();
  await page.getByRole("link", { name: "Saved", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Saved reading" })).toBeVisible();
  await expect(page.getByRole("article").getByText("Async Python agents are getting cheaper to operate")).toBeVisible();
  await expect(page.getByRole("article").getByRole("link", { name: "Open source" })).toHaveAttribute("href", /^https:/);
  await page.getByRole("article").getByRole("button", { name: "Remove" }).click();
  await expect(page.getByRole("heading", { name: "Save a useful piece from today’s picks" })).toBeVisible();
});

test("records content click events from public picks", async ({ page }) => {
  let payload: { content_id?: string; type?: string } | undefined;
  await page.addInitScript(() => localStorage.setItem("codepick_token", "demo.token"));
  await page.route("**/api/events", async (route) => {
    payload = route.request().postDataJSON();
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true }) });
  });
  await page.goto("/en");
  await page.getByRole("article").getByRole("link", { name: "Async Python agents are getting cheaper to operate" }).click();
  await expect(page).toHaveURL(/\/en\/items\/cp-001$/);
  expect(payload).toEqual({ content_id: "cp-001", type: "click" });
});

test("renders bilingual fixture detail, provenance, and SEO data", async ({ page }) => {
  await page.goto("/zh/items/cp-001");
  await expect(page.getByRole("heading", { name: "异步 Python 智能体的运行成本正在下降" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "原文摘录" })).toBeVisible();
  await expect(page.getByText("当前摘录与译文来自测试样例")).toBeVisible();
  await expect(page.getByText("六维评分")).toBeVisible();
  await expect(page.locator('script[type="application/ld+json"]')).toHaveCount(1);
});

test("records reader behavior actions only after reader API confirmation", async ({ page }) => {
  const calls: string[] = [];
  await page.addInitScript(() => localStorage.setItem("codepick_token", "demo.token"));
  await page.route("**/api/events", async (route) => {
    calls.push("events");
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true }) });
  });
  await page.route("**/api/bookmarks", async (route) => {
    calls.push("bookmarks");
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true }) });
  });
  await page.goto("/en/items/cp-001");
  await page.getByRole("button", { name: "Mark as read" }).click();
  await expect(page.getByText("Read status saved to your account.")).toBeVisible();
  await page.getByRole("button", { name: "Save to account" }).click();
  await expect(page.getByText("Saved to your account.")).toBeVisible();
  await page.getByRole("button", { name: "Less like this" }).click();
  await expect(page.getByText("Preference saved to your account.")).toBeVisible();
  expect(calls).toEqual(["events", "bookmarks", "events"]);
});

test("does not claim an account action succeeded while the API is offline", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("codepick_token", "demo.token"));
  await page.route("**/api/bookmarks", async (route) => route.abort("failed"));
  await page.goto("/en/items/cp-001");
  await page.getByRole("button", { name: "Save to account" }).click();
  await expect(page.getByText(/did not confirm this action/)).toBeVisible();
  await expect(page.getByText("Saved to your account.")).toHaveCount(0);
});

test("sitemap exposes localized detail, brief, and saved routes", async ({ page }) => {
  const response = await page.goto("/sitemap.xml");
  expect(response?.ok()).toBeTruthy();
  const body = await page.textContent("body");
  expect(body).toContain("https://codepick.example/en/items/cp-001");
  expect(body).toContain("https://codepick.example/zh/items/cp-001");
  expect(body).toContain("https://codepick.example/en/brief");
  expect(body).toContain("https://codepick.example/zh/library");
});

test("renders the public daily brief without fake queue metrics", async ({ page }) => {
  await page.goto("/en/brief");
  await expect(page.getByRole("heading", { name: "Daily brief" })).toBeVisible();
  await expect(page.getByText("Personal briefs remain a capability to validate.")).toBeVisible();
  await expect(page.getByText("Queue-backed agent systems")).toBeVisible();
  await expect(page.getByText(/Arq \/ Email/)).toHaveCount(0);
});

test("keeps failed development login signed out and confirms brief only after an API response", async ({ page }) => {
  let loginRequestUrl = "";
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/auth/login") loginRequestUrl = request.url();
  });
  await page.route("**/api/brief/me", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: "personal-demo", items: [] }) });
  });
  await page.goto("/en/login");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByText("Sign-in failed. No development session was created.")).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("codepick_token"))).toBeNull();
  await expect.poll(() => loginRequestUrl).not.toBe("");
  expect(new URL(loginRequestUrl).origin).toBe(new URL(page.url()).origin);
  expect(loginRequestUrl).not.toContain("127.0.0.1:8000");

  await page.evaluate(() => {
    localStorage.setItem("codepick_token", "server-confirmed.test.token");
    localStorage.setItem("codepick_plan", "pro");
  });
  await page.goto("/en/brief");
  await expect(page.getByText("Personal brief confirmed by the API")).toBeVisible();
});

test("keeps a real session and local saves when bookmark sync fails or local data is corrupt", async ({ page }) => {
  let loginCount = 0;
  let bookmarkCalls = 0;
  await page.addInitScript(() => {
    localStorage.setItem("cp_saved", JSON.stringify(["cp-001"]));
    localStorage.setItem("cp_saved_items", JSON.stringify([{ id: "cp-001", title: "Saved fixture" }]));
  });
  await page.route("**/api/auth/login", async (route) => {
    loginCount += 1;
    const body = route.request().postDataJSON() as { email: string };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ token: "real-session-" + loginCount, user: { email: body.email, locale: "en", plan: "free", is_admin: false } })
    });
  });
  await page.route("**/api/bookmarks", async (route) => {
    bookmarkCalls += 1;
    await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "temporarily unavailable" }) });
  });

  await page.goto("/en/login");
  await page.getByLabel("Email").fill("sync-failure@example.com");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByText("Signed in, but local saves were not synced. They remain on this device.")).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("codepick_token"))).toBe("real-session-1");
  expect(await page.evaluate(() => localStorage.getItem("codepick_plan"))).toBe("free");
  expect(await page.evaluate(() => localStorage.getItem("codepick_is_admin"))).toBe("false");
  expect(await page.evaluate(() => localStorage.getItem("cp_saved"))).toBe(JSON.stringify(["cp-001"]));
  expect(await page.evaluate(() => localStorage.getItem("cp_saved_items"))).toContain("Saved fixture");

  await page.evaluate(() => localStorage.setItem("cp_saved", "{not-json"));
  await page.getByLabel("Email").fill("dirty-saves@example.com");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect.poll(() => page.evaluate(() => localStorage.getItem("codepick_token"))).toBe("real-session-2");
  await expect(page.getByText("Signed in, but local saves were not synced. They remain on this device.")).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("cp_saved"))).toBe("{not-json");
  expect(bookmarkCalls).toBe(1);
});

test("renders localized Chinese account controls without mojibake", async ({ page }) => {
  await page.goto("/zh/login");
  await expect(page.getByRole("heading", { name: "登录" })).toBeVisible();
  await expect(page.getByLabel("邮箱")).toBeVisible();
  await expect(page.getByText(/不验证邮箱所有权/)).toBeVisible();
  await expect(page.getByRole("button", { name: "继续" })).toBeVisible();
  await page.goto("/zh/pricing");
  await expect(page.getByRole("button", { name: "$8 月付" })).toBeVisible();
  await expect(page.getByRole("button", { name: "$79 年付" })).toBeVisible();
  await expect(page.getByRole("button", { name: "$4.9 早鸟" })).toBeVisible();
  await expect(page.locator("body")).not.toContainText("\u9427");
});

test("saves interests and renders only recommendations returned by reader API", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("codepick_token", "confirmed.test.token"));
  const calls: string[] = [];
  await page.route("**/api/interests", async (route) => {
    calls.push("interests");
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true, count: 5 }) });
  });
  await page.route("**/api/recommendations", async (route) => {
    calls.push("recommendations");
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [{ id: "cp-001", title: "Async Python agents are getting cheaper to operate", source: "CodePick Research" }] }) });
  });
  await page.goto("/en/login");
  await page.getByRole("button", { name: "Save interests" }).click();
  await expect(page.getByText("Interests saved by the Reader API")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Returned recommendations" })).toBeVisible();
  await expect(page.getByText("CodePick Research")).toBeVisible();
  expect(calls).toEqual(["interests", "recommendations"]);
});

test("reports companion unavailability without inventing an answer", async ({ page }) => {
  await page.goto("/en/items/cp-001");
  await expect(page.getByRole("heading", { name: "Reading companion" })).toBeVisible();
  await page.getByRole("button", { name: "Ask" }).click();
  await expect(page.getByText(/no answer was generated/)).toBeVisible();
  await expect(page.getByText(/Local companion/)).toHaveCount(0);
});

test("supports sandbox checkout fallback", async ({ page }) => {
  await page.goto("/en/pricing");
  await page.getByRole("button", { name: "$8 monthly" }).click();
  await expect(page.getByText("Sandbox checkout:")).toBeVisible();
  await expect(page.getByText("currency=USD")).toBeVisible();
});

test("supports local API key lifecycle fallback", async ({ page }) => {
  await page.goto("/en/developers");
  await expect(page.getByRole("heading", { name: "Public API keys" })).toBeVisible();
  await page.getByRole("button", { name: "Create key" }).click();
  await expect(page.getByText("New key:")).toBeVisible();
  await expect(page.getByText("Local demo API key created")).toBeVisible();
  await expect(page.getByText(/New key: cp_demo_/)).toBeVisible();
  await page.getByRole("button", { name: "Revoke" }).first().click();
  await expect(page.getByText("Local demo API key revoked")).toBeVisible();
});

test("keeps a real API key active when server-side revocation fails", async ({ page }) => {
  await page.route("**/api/api-keys", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [{ prefix: "cp_live_", scopes: ["read"], rate_limit_rpm: 60, daily_quota: 1000, status: "active" }] })
    });
  });
  await page.route("**/api/api-keys/cp_live_", async (route) => {
    await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "temporarily unavailable" }) });
  });
  await page.goto("/en/developers");
  await expect(page.getByText(/cp_live_.*active/)).toBeVisible();
  await page.getByRole("button", { name: "Revoke" }).click();
  await expect(page.getByText("API key was not revoked. The Reader API rejected the request; try again.")).toBeVisible();
  await expect(page.getByText(/cp_live_.*active/)).toBeVisible();
  await expect(page.getByText(/cp_live_.*revoked/)).toHaveCount(0);
});

test("admin taxonomy shell manages categories and audiences", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("codepick_token", "demo.admin.token");
    localStorage.setItem("codepick_is_admin", "true");
  });
  await page.route("**/api/admin/categories", async (route) => {
    await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "temporarily unavailable" }) });
  });
  await page.route("**/api/admin/audiences", async (route) => {
    await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "temporarily unavailable" }) });
  });
  await page.goto("/en/admin");
  await expect(page.getByRole("heading", { name: "Categories and audiences" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Category manager" })).toBeVisible();
  await page.getByLabel("Category code").fill("ops");
  await page.getByRole("button", { name: "Add category" }).click();
  await expect(page.getByText("Category save failed")).toBeVisible();
  await page.getByLabel("Audience code").fill("operators");
  await page.getByRole("button", { name: "Add audience" }).click();
  await expect(page.getByText("Audience save failed")).toBeVisible();
});
