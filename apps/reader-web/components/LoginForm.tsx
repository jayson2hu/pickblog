"use client";

import { FormEvent, useState } from "react";
import { clientApiUrl } from "../lib/client-api";

const requestTimeoutMs = 10000;
const copy = {
  en: {
    email: "Email", continue: "Continue", signedIn: "Signed in",
    loginFailed: "Sign-in failed. No development session was created.",
    syncFailed: "Signed in, but local saves were not synced. They remain on this device.",
    boundary: "Development sign-in does not verify email ownership. Plan and admin access come only from the Reader API.",
    synced: (count: number) => "Synced " + count + " saved item" + (count === 1 ? "" : "s")
  },
  zh: {
    email: "\u90ae\u7bb1", continue: "\u7ee7\u7eed", signedIn: "\u5df2\u767b\u5f55",
    loginFailed: "\u767b\u5f55\u5931\u8d25\uff0c\u672a\u521b\u5efa\u5f00\u53d1\u4f1a\u8bdd\u3002",
    syncFailed: "\u5df2\u767b\u5f55\uff0c\u4f46\u672c\u673a\u6536\u85cf\u672a\u540c\u6b65\uff1b\u5b83\u4eec\u4ecd\u4fdd\u7559\u5728\u5f53\u524d\u6d4f\u89c8\u5668\u3002",
    boundary: "\u5f00\u53d1\u767b\u5f55\u4e0d\u9a8c\u8bc1\u90ae\u7bb1\u6240\u6709\u6743\uff1b\u5957\u9910\u548c\u7ba1\u7406\u5458\u6743\u9650\u53ea\u4ee5 Reader API \u8fd4\u56de\u4e3a\u51c6\u3002",
    synced: (count: number) => "\u5df2\u540c\u6b65 " + count + " \u6761\u7a0d\u540e\u8bfb"
  }
};

export function LoginForm({ locale }: { locale: string }) {
  const t = copy[locale as "en" | "zh"] ?? copy.en;
  const [email, setEmail] = useState("dev@example.com");
  const [status, setStatus] = useState("");

  async function syncSaved(token: string) {
    const parsed = JSON.parse(localStorage.getItem("cp_saved") ?? "[]") as unknown;
    if (!Array.isArray(parsed)) throw new Error("invalid local saves");
    const saved = [...new Set(parsed.filter((item): item is string => typeof item === "string" && item.length > 0))];
    if (!saved.length) return 0;
    for (const contentId of saved) {
      const response = await fetch(clientApiUrl("/api/bookmarks"), {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
        body: JSON.stringify({ content_id: contentId, note: "saved from reader", highlights: [] })
      });
      if (!response.ok) throw new Error("bookmark sync failed");
    }
    localStorage.removeItem("cp_saved");
    localStorage.removeItem("cp_saved_items");
    window.dispatchEvent(new CustomEvent("codepick:saved-change"));
    return saved.length;
  }

  function clearSession() {
    localStorage.removeItem("codepick_token");
    localStorage.removeItem("codepick_plan");
    localStorage.removeItem("codepick_email");
    localStorage.removeItem("codepick_is_admin");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), requestTimeoutMs);
    try {
      const response = await fetch(clientApiUrl("/api/auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, locale }),
        signal: controller.signal
      });
      if (!response.ok) throw new Error("login failed");
      const body = await response.json();
      if (typeof body.token !== "string" || !body.user || typeof body.user.plan !== "string") throw new Error("invalid login response");
      localStorage.setItem("codepick_token", body.token);
      localStorage.setItem("codepick_plan", body.user.plan);
      localStorage.setItem("codepick_email", body.user.email ?? email);
      localStorage.setItem("codepick_is_admin", String(body.user.is_admin === true));
      try {
        const synced = await syncSaved(body.token);
        setStatus(synced ? t.synced(synced) : t.signedIn);
      } catch {
        setStatus(t.syncFailed);
      }
    } catch {
      clearSession();
      setStatus(t.loginFailed);
    } finally {
      window.clearTimeout(timeout);
    }
  }

  return (
    <form className="tool-panel grid gap-4" onSubmit={submit}>
      <div>
        <h2 className="section-title">{locale === "zh" ? "\u4f1a\u8bdd" : "Session"}</h2>
        <p className="mt-1 text-sm text-muted">{t.boundary}</p>
      </div>
      <label className="grid gap-1 text-sm">
        {t.email}
        <input className="rounded-md border border-line bg-white px-3 py-2" name="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
      </label>
      <button className="primary-button" type="submit">
        {t.continue}
      </button>
      {status ? <p className="text-sm text-accent" role="status">{status}</p> : null}
    </form>
  );
}
