"use client";

import { FormEvent, useState } from "react";

const apiBase = process.env.NEXT_PUBLIC_READER_API_BASE ?? "http://127.0.0.1:8000";
const requestTimeoutMs = 900;
const copy = {
  en: { email: "Email", plan: "Plan", free: "Free", pro: "Pro", continue: "Continue", synced: (count: number) => `Synced ${count} saved item${count === 1 ? "" : "s"}` },
  zh: { email: "\u90ae\u7bb1", plan: "\u5957\u9910", free: "\u514d\u8d39", pro: "Pro", continue: "\u7ee7\u7eed", synced: (count: number) => `已同步 ${count} 条稍后读` }
};

export function LoginForm({ locale }: { locale: string }) {
  const t = copy[locale as "en" | "zh"] ?? copy.en;
  const [email, setEmail] = useState("dev@example.com");
  const [plan, setPlan] = useState("free");
  const [status, setStatus] = useState("");

  async function syncSaved(token: string) {
    const saved = JSON.parse(localStorage.getItem("cp_saved") ?? "[]") as string[];
    if (!saved.length) return 0;
    for (const contentId of saved) {
      const response = await fetch(`${apiBase}/api/bookmarks`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ content_id: contentId, note: "saved from reader", highlights: [] })
      });
      if (!response.ok) throw new Error("bookmark sync failed");
    }
    localStorage.removeItem("cp_saved");
    return saved.length;
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), requestTimeoutMs);
    try {
      const response = await fetch(`${apiBase}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, locale, plan }),
        signal: controller.signal
      });
      if (!response.ok) throw new Error("login failed");
      const body = await response.json();
      localStorage.setItem("codepick_token", body.token);
      localStorage.setItem("codepick_plan", body.user.plan);
      localStorage.setItem("codepick_email", body.user.email ?? email);
      localStorage.setItem("codepick_is_admin", String(body.user.is_admin ?? email.startsWith("admin")));
      const synced = await syncSaved(body.token);
      setStatus(synced ? t.synced(synced) : locale === "zh" ? "\u5df2\u767b\u5f55" : "Signed in");
    } catch {
      localStorage.setItem("codepick_token", `demo.${btoa(JSON.stringify({ email, plan }))}.token`);
      localStorage.setItem("codepick_plan", plan);
      localStorage.setItem("codepick_email", email);
      localStorage.setItem("codepick_is_admin", String(email.startsWith("admin")));
      setStatus(locale === "zh" ? "\u5df2\u8fdb\u5165\u672c\u5730\u6f14\u793a\u4f1a\u8bdd" : "Local demo session active");
    } finally {
      window.clearTimeout(timeout);
    }
  }

  return (
    <form className="tool-panel grid gap-4" onSubmit={submit}>
      <div>
        <h2 className="section-title">{locale === "zh" ? "\u4f1a\u8bdd" : "Session"}</h2>
        <p className="mt-1 text-sm text-muted">{locale === "zh" ? "\u672c\u5730\u6f14\u793a\u5728 API \u4e0d\u53ef\u7528\u65f6\u4ecd\u53ef\u8fd0\u884c\u3002" : "Local demo mode remains usable when the API is offline."}</p>
      </div>
      <label className="grid gap-1 text-sm">
        {t.email}
        <input className="rounded-md border border-line bg-white px-3 py-2" name="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
      </label>
      <label className="grid gap-1 text-sm">
        {t.plan}
        <select className="rounded-md border border-line bg-white px-3 py-2" value={plan} onChange={(event) => setPlan(event.target.value)}>
          <option value="free">{t.free}</option>
          <option value="pro">{t.pro}</option>
        </select>
      </label>
      <button className="primary-button" type="submit">
        {t.continue}
      </button>
      {status ? <p className="text-sm text-accent">{status}</p> : null}
    </form>
  );
}
