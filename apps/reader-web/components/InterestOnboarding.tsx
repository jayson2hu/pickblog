"use client";

import { useState } from "react";
import { clientApiUrl } from "../lib/client-api";
import { TrackedContentLink } from "./TrackedContentLink";

type Recommendation = { id: string; title: string; source: string };
const topics = [
  { code: "ai", en: "AI", zh: "AI" }, { code: "backend", en: "Backend", zh: "后端" },
  { code: "frontend", en: "Frontend", zh: "前端" }, { code: "data", en: "Data", zh: "数据" },
  { code: "security", en: "Security", zh: "安全" }, { code: "devops", en: "DevOps", zh: "DevOps" },
  { code: "product", en: "Product", zh: "产品" }, { code: "research", en: "Research", zh: "研究" }
];
const copy = {
  en: { title: "Local interests", subtitle: "Choose 5–8 topics. They stay on this device unless the Reader API confirms a save.", save: "Save interests", saved: "Interests saved by the Reader API", localSaved: "Saved on this device; recommendations are unavailable", pickRange: "Choose 5–8 topics", signInRequired: "Use a development session first", recommendations: "Returned recommendations" },
  zh: { title: "本机兴趣", subtitle: "选择 5–8 个主题。只有 Reader API 确认后才会同步到账户，否则仅保存在本机。", save: "保存兴趣", saved: "Reader API 已保存兴趣", localSaved: "已保存在本机；当前没有可用推荐", pickRange: "请选择 5–8 个主题", signInRequired: "请先使用开发会话", recommendations: "接口返回的推荐" }
};

export function InterestOnboarding({ locale }: { locale: string }) {
  const t = copy[locale as "en" | "zh"] ?? copy.en;
  const [selected, setSelected] = useState<string[]>(topics.slice(0, 5).map((topic) => topic.code));
  const [status, setStatus] = useState("");
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [saving, setSaving] = useState(false);
  function toggle(code: string) { setSelected((current) => current.includes(code) ? current.filter((item) => item !== code) : [...current, code]); }
  async function save() {
    if (saving) return;
    if (selected.length < 5 || selected.length > 8) { setStatus(t.pickRange); return; }
    setSaving(true);
    const token = localStorage.getItem("codepick_token");
    try {
      const saveResponse = await fetch(clientApiUrl("/api/interests"), { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token ?? ""}` }, body: JSON.stringify({ tags: selected }) });
      if (saveResponse.status === 401 || saveResponse.status === 403) { setStatus(t.signInRequired); return; }
      if (!saveResponse.ok) throw new Error("interests unavailable");
      const recommendationResponse = await fetch(clientApiUrl("/api/recommendations"), { headers: { Authorization: `Bearer ${token ?? ""}` } });
      if (!recommendationResponse.ok) throw new Error("recommendations unavailable");
      const body = await recommendationResponse.json();
      setRecommendations(body.items ?? []);
      setStatus(t.saved);
    } catch {
      localStorage.setItem("codepick_interests", JSON.stringify(selected));
      setRecommendations([]);
      setStatus(t.localSaved);
    } finally { setSaving(false); }
  }

  return <section className="tool-panel"><h2 className="section-title">{t.title}</h2><p className="mt-1 text-sm leading-6 text-muted">{t.subtitle}</p>
    <div className="mt-4 flex flex-wrap gap-2">{topics.map((topic) => { const active = selected.includes(topic.code); return <button key={topic.code} aria-pressed={active} className={`chip${active ? " chip-active" : ""}`} type="button" onClick={() => toggle(topic.code)}>{locale === "zh" ? topic.zh : topic.en}</button>; })}</div>
    <button className="primary-button mt-4" type="button" onClick={save} disabled={saving}>{t.save}</button>
    {status ? <p className="mt-3 text-sm text-accent" role="status">{status}</p> : null}
    {recommendations.length ? <div className="mt-4"><h3 className="text-sm font-bold">{t.recommendations}</h3><ul className="mt-2 grid gap-2 text-sm text-muted">{recommendations.map((item) => <li key={item.id}><TrackedContentLink className="font-medium text-ink" contentId={item.id} href={`/${locale}/items/${item.id}`}>{item.title}</TrackedContentLink> <span>{item.source}</span></li>)}</ul></div> : null}
  </section>;
}
