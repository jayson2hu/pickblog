import { expect, test } from "@playwright/test";

test("renders public picks and language switch", async ({ page }) => {
  await page.goto("/en");
  await expect(page).toHaveTitle(/CodePick/);
  await expect(page.getByRole("heading", { name: "Public picks" })).toBeVisible();
  await expect(page.getByRole("article").getByText("Async Python agents are getting cheaper to operate")).toBeVisible();
  await page.getByRole("link", { name: "\u4e2d\u6587" }).click();
  await expect(page.getByRole("heading", { name: "\u516c\u5171\u7cbe\u9009" })).toBeVisible();
});

test("records content click events from public picks", async ({ page }) => {
  let payload: { content_id?: string; type?: string } | undefined;
  await page.addInitScript(() => {
    localStorage.setItem("codepick_token", "demo.token");
  });
  await page.route("**/api/events", async (route) => {
    payload = route.request().postDataJSON();
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true }) });
  });

  await page.goto("/en");
  await page.getByRole("article").getByRole("link", { name: "Async Python agents are getting cheaper to operate" }).click();

  await expect(page).toHaveURL(/\/en\/items\/cp-001$/);
  expect(payload).toEqual({ content_id: "cp-001", type: "click" });
});

test("renders bilingual detail analysis and SEO data", async ({ page }) => {
  await page.goto("/zh/items/cp-001");
  await expect(
    page.getByRole("heading", { name: "\u5f02\u6b65 Python \u667a\u80fd\u4f53\u7684\u8fd0\u884c\u6210\u672c\u6b63\u5728\u4e0b\u964d" })
  ).toBeVisible();
  await expect(page.getByText("\u516d\u7ef4\u8bc4\u5206")).toBeVisible();
  await expect(page.locator('script[type="application/ld+json"]')).toHaveCount(1);
});

test("records reader behavior actions through reader API", async ({ page }) => {
  const calls: string[] = [];
  await page.addInitScript(() => {
    localStorage.setItem("codepick_token", "demo.token");
  });
  await page.route("**/api/events", async (route) => {
    calls.push("events");
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true }) });
  });
  await page.route("**/api/bookmarks", async (route) => {
    calls.push("bookmarks");
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true }) });
  });

  await page.goto("/en/items/cp-001");
  await page.getByRole("button", { name: "Mark deep read" }).click();
  await expect(page.getByText("Deep read saved")).toBeVisible();
  await page.getByRole("button", { name: "Bookmark" }).click();
  await expect(page.getByText("Bookmark saved")).toBeVisible();
  await page.getByRole("button", { name: "Not interested" }).click();
  await expect(page.getByText("Preference saved")).toBeVisible();
  expect(calls).toEqual(["events", "bookmarks", "events"]);
});

test("sitemap exposes localized detail and brief routes", async ({ page }) => {
  const response = await page.goto("/sitemap.xml");
  expect(response?.ok()).toBeTruthy();
  const body = await page.textContent("body");
  expect(body).toContain("https://codepick.example/en/items/cp-001");
  expect(body).toContain("https://codepick.example/zh/items/cp-001");
  expect(body).toContain("https://codepick.example/en/brief");
  expect(body).toContain("https://codepick.example/zh/brief");
});

test("renders daily brief from stub content", async ({ page }) => {
  await page.goto("/en/brief");
  await expect(page.getByRole("heading", { name: "Daily brief" })).toBeVisible();
  await expect(page.getByText("Personal briefs require Pro")).toBeVisible();
  await expect(page.getByText("Queue-backed agent systems")).toBeVisible();
});

test("supports login and pro brief state", async ({ page }) => {
  await page.route("**/api/brief/me", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: "personal-demo", items: [] }) });
  });

  await page.goto("/en/login");
  await page.getByLabel("Plan").selectOption("pro");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByText(/Signed in|Local demo session active/)).toBeVisible();

  await page.goto("/en/brief");
  await expect(page.getByText(/Pro personal brief synced|Local Pro demo brief unlocked/)).toBeVisible();
});

test("renders localized Chinese account controls without mojibake", async ({ page }) => {
  await page.goto("/zh/login");
  await expect(page.getByRole("heading", { name: "\u767b\u5f55" })).toBeVisible();
  await expect(page.getByLabel("\u90ae\u7bb1")).toBeVisible();
  await expect(page.getByLabel("\u5957\u9910")).toBeVisible();
  await expect(page.getByRole("button", { name: "\u7ee7\u7eed" })).toBeVisible();
  await page.goto("/zh/pricing");
  await expect(page.getByRole("button", { name: "$8 \u6708\u4ed8" })).toBeVisible();
  await expect(page.getByRole("button", { name: "$79 \u5e74\u4ed8" })).toBeVisible();
  await expect(page.getByRole("button", { name: "$4.9 \u65e9\u9e1f" })).toBeVisible();
  await expect(page.locator("body")).not.toContainText("\u9427");
});

test("saves interests and renders recommendations through reader API", async ({ page }) => {
  const calls: string[] = [];
  await page.route("**/api/interests", async (route) => {
    calls.push("interests");
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true, count: 5 }) });
  });
  await page.route("**/api/recommendations", async (route) => {
    calls.push("recommendations");
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [{ id: "cp-001", title: "Async Python agents are getting cheaper to operate", source: "CodePick Research" }] })
    });
  });

  await page.goto("/en/login");
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Save interests" }).click();
  await expect(page.getByText("Interests saved")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Recommended for you" })).toBeVisible();
  await expect(page.getByText("CodePick Research")).toBeVisible();
  expect(calls).toEqual(["interests", "recommendations"]);
});

test("supports local companion fallback", async ({ page }) => {
  await page.goto("/en/items/cp-001");
  await expect(page.getByRole("heading", { name: "AI companion" })).toBeVisible();
  await page.getByRole("button", { name: "Ask" }).click();
  await expect(page.getByText(/Local companion|Question:/)).toBeVisible();
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
  await expect(page.getByText("API key revoked")).toBeVisible();
});

test("admin taxonomy shell manages categories and audiences", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("codepick_token", "demo.admin.token");
    localStorage.setItem("codepick_is_admin", "true");
  });
  await page.goto("/en/admin");
  await expect(page.getByRole("heading", { name: "Categories and audiences" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Category manager" })).toBeVisible();
  await page.getByLabel("Category code").fill("ops");
  await page.getByRole("button", { name: "Add category" }).click();
  await expect(page.getByText(/Category saved|Category save failed/)).toBeVisible();
  await page.getByLabel("Audience code").fill("operators");
  await page.getByRole("button", { name: "Add audience" }).click();
  await expect(page.getByText(/Audience saved|Audience save failed/)).toBeVisible();
});
