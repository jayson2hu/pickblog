"use client";

import { useEffect, useState } from "react";
import { clientApiUrl } from "../lib/client-api";
import { readSavedItems } from "../lib/saved";
import { getMe } from "../lib/session";

export function Sidebar({ locale }: { locale: string }) {
  const [plan, setPlan] = useState<"anonymous" | "free" | "pro">("anonymous");
  const [savedCount, setSavedCount] = useState(0);
  const [interests, setInterests] = useState<string[]>([]);
  const isZh = locale === "zh";

  useEffect(() => {
    const refreshSaved = () => setSavedCount(readSavedItems().length);
    refreshSaved();
    window.addEventListener("codepick:saved-change", refreshSaved);
    const token = localStorage.getItem("codepick_token");
    void getMe(token).then((profile) => setPlan(profile ? (profile.plan === "pro" ? "pro" : "free") : "anonymous"));
    try { setInterests(JSON.parse(localStorage.getItem("codepick_interests") ?? "[]")); } catch { setInterests([]); }
    if (token) {
      fetch(clientApiUrl("/api/interests"), { headers: { Authorization: `Bearer ${token}` } })
        .then((response) => { if (!response.ok) throw new Error("interests unavailable"); return response.json(); })
        .then((body) => setInterests((body.interests ?? body.items ?? []).map((item: string | { topic?: string; label?: string }) => typeof item === "string" ? item : item.label ?? item.topic).filter(Boolean)))
        .catch(() => undefined);
    }
    return () => window.removeEventListener("codepick:saved-change", refreshSaved);
  }, []);

  return (
    <aside className="sidebar-panel">
      <div>
        <p className="metric-label">{isZh ? "你的阅读台" : "Your reading desk"}</p>
        <h2 className="mt-2 text-xl font-bold tracking-normal">{plan === "pro" ? (isZh ? "本地 Pro 测试会话" : "Local Pro test session") : plan === "free" ? (isZh ? "本地 Free 会话" : "Local Free session") : isZh ? "游客模式" : "Guest mode"}</h2>
        <p className="mt-2 text-sm leading-6 text-muted">{isZh ? "游客收藏保存在当前浏览器，可随时从收藏页回看。" : "Guest saves stay in this browser and remain available from Saved."}</p>
      </div>
      <a className="sidebar-stat" href={`/${locale}/library`}><span>{savedCount}</span><small>{isZh ? "篇本机收藏" : "saved on this device"}</small></a>
      {interests.length ? <div className="grid gap-2 text-sm text-muted"><strong className="text-ink">{isZh ? "本机兴趣" : "Local interests"}</strong><span>{interests.join(isZh ? "、" : ", ")}</span></div> : <p className="text-sm leading-6 text-muted">{isZh ? "尚未设置兴趣；当前队列不会声称已个性化。" : "No interests set; this queue does not claim to be personalized."}</p>}
      <a className="secondary-button" href={`/${locale}/library`}>{isZh ? "打开收藏" : "Open saved"}</a>
      {plan === "anonymous" ? <a className="text-link" href={`/${locale}/login`}>{isZh ? "使用本地开发身份" : "Use a local development identity"}</a> : null}
    </aside>
  );
}
