"use client";

import { useState } from "react";

import { TrackedContentLink } from "./TrackedContentLink";

const apiBase = process.env.NEXT_PUBLIC_READER_API_BASE ?? "http://127.0.0.1:8000";

type Recommendation = { id: string; title: string; source: string };

const topics = [
  { code: "ai", en: "AI", zh: "AI" },
  { code: "backend", en: "Backend", zh: "\u540e\u7aef" },
  { code: "frontend", en: "Frontend", zh: "\u524d\u7aef" },
  { code: "data", en: "Data", zh: "\u6570\u636e" },
  { code: "security", en: "Security", zh: "\u5b89\u5168" },
  { code: "devops", en: "DevOps", zh: "DevOps" },
  { code: "product", en: "Product", zh: "\u4ea7\u54c1" },
  { code: "research", en: "Research", zh: "\u7814\u7a76" }
];

const copy = {
  en: {
    title: "Interest onboarding",
    subtitle: "Choose 5-8 topics to seed your L3 recommendations.",
    save: "Save interests",
    saved: "Interests saved",
    localSaved: "Local interests saved",
    pickRange: "Choose 5-8 topics",
    signInRequired: "Sign in required",
    recommendations: "Recommended for you"
  },
  zh: {
    title: "\u5174\u8da3\u5f15\u5bfc",
    subtitle: "\u9009\u62e9 5-8 \u4e2a\u4e3b\u9898\uff0c\u7528\u4e8e L3 \u63a8\u8350\u3002",
    save: "\u4fdd\u5b58\u5174\u8da3",
    saved: "\u5174\u8da3\u5df2\u4fdd\u5b58",
    localSaved: "\u672c\u5730\u5174\u8da3\u5df2\u4fdd\u5b58",
    pickRange: "\u8bf7\u9009\u62e9 5-8 \u4e2a\u4e3b\u9898",
    signInRequired: "\u9700\u8981\u767b\u5f55",
    recommendations: "\u4e3a\u4f60\u63a8\u8350"
  }
};

export function InterestOnboarding({ locale }: { locale: string }) {
  const t = copy[locale as "en" | "zh"] ?? copy.en;
  const [selected, setSelected] = useState<string[]>(topics.slice(0, 5).map((topic) => topic.code));
  const [status, setStatus] = useState("");
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [saving, setSaving] = useState(false);

  function toggle(code: string) {
    setSelected((current) => (current.includes(code) ? current.filter((item) => item !== code) : [...current, code]));
  }

  async function save() {
    if (saving) return;
    if (selected.length < 5 || selected.length > 8) {
      setStatus(t.pickRange);
      return;
    }

    setSaving(true);
    const token = localStorage.getItem("codepick_token");
    try {
      const saveResponse = await fetch(`${apiBase}/api/interests`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token ?? ""}` },
        body: JSON.stringify({ tags: selected })
      });
      if (saveResponse.status === 401 || saveResponse.status === 403) {
        setStatus(t.signInRequired);
        return;
      }
      if (!saveResponse.ok) throw new Error("interests unavailable");

      const recommendationResponse = await fetch(`${apiBase}/api/recommendations`, { headers: { Authorization: `Bearer ${token ?? ""}` } });
      if (!recommendationResponse.ok) throw new Error("recommendations unavailable");
      const body = await recommendationResponse.json();
      setRecommendations(body.items ?? []);
      setStatus(t.saved);
    } catch {
      localStorage.setItem("codepick_interests", JSON.stringify(selected));
      setRecommendations([{ id: "cp-001", title: "Async Python agents are getting cheaper to operate", source: "CodePick Research" }]);
      setStatus(t.localSaved);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="tool-panel">
      <h2 className="section-title">{t.title}</h2>
      <p className="mt-1 text-sm text-muted">{t.subtitle}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {topics.map((topic) => {
          const active = selected.includes(topic.code);
          return (
            <button
              key={topic.code}
              className={`rounded-md border px-3 py-2 text-sm font-semibold ${active ? "border-ink bg-ink text-white" : "border-line bg-white text-ink"}`}
              type="button"
              onClick={() => toggle(topic.code)}
            >
              {locale === "zh" ? topic.zh : topic.en}
            </button>
          );
        })}
      </div>
      <button className="primary-button mt-4" type="button" onClick={save} disabled={saving}>
        {t.save}
      </button>
      {status ? <p className="mt-3 text-sm text-accent">{status}</p> : null}
      {recommendations.length ? (
        <div className="mt-4">
          <h3 className="text-sm font-bold">{t.recommendations}</h3>
          <ul className="mt-2 grid gap-2 text-sm text-muted">
            {recommendations.map((item) => (
              <li key={item.id}>
                <TrackedContentLink className="font-medium text-ink" contentId={item.id} href={`/${locale}/items/${item.id}`}>
                  {item.title}
                </TrackedContentLink>{" "}
                <span>{item.source}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
