"use client";

import { useEffect, useState } from "react";
import { apiBase } from "../lib/api";
import { getMe } from "../lib/session";

const savedKey = "cp_saved";

export function Sidebar({ locale }: { locale: string }) {
  const [plan, setPlan] = useState<"anonymous" | "free" | "pro">("anonymous");
  const [savedCount, setSavedCount] = useState(0);
  const [interests, setInterests] = useState<string[]>([]);

  useEffect(() => {
    const token = localStorage.getItem("codepick_token");
    void getMe(token).then((profile) => setPlan(profile ? (profile.plan === "pro" ? "pro" : "free") : "anonymous"));
    try {
      setSavedCount(JSON.parse(localStorage.getItem(savedKey) ?? "[]").length);
    } catch {
      setSavedCount(0);
    }
    if (!token) {
      setInterests(locale === "zh" ? ["AI", "工程", "数据"] : ["AI", "engineering", "data"]);
      return;
    }
    fetch(`${apiBase}/api/interests`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => {
        if (!response.ok) throw new Error("interests unavailable");
        return response.json();
      })
      .then((body) => setInterests((body.interests ?? body.items ?? []).map((item: string | { topic?: string; label?: string }) => (typeof item === "string" ? item : item.label ?? item.topic)).filter(Boolean)))
      .catch(() => setInterests(locale === "zh" ? ["AI", "工程", "数据"] : ["AI", "engineering", "data"]));
  }, [locale]);

  const isZh = locale === "zh";
  return (
    <aside className="sidebar-panel">
      <div>
        <p className="metric-label">{isZh ? "当前状态" : "Reader state"}</p>
        <h2 className="mt-2 text-xl font-bold tracking-normal">
          {plan === "pro" ? "CodePick Pro" : plan === "free" ? (isZh ? "已登录 Free" : "Signed-in Free") : isZh ? "未登录阅读" : "Anonymous reading"}
        </h2>
      </div>
      <div className="sidebar-stat">
        <span>{savedCount}</span>
        <small>{isZh ? "稍后读" : "saved for later"}</small>
      </div>
      <div className="grid gap-2 text-sm text-muted">
        <span>{isZh ? `关注领域：${interests.join("、")}` : `Following: ${interests.join(", ")}`}</span>
        <span>{isZh ? "早报：公共精选已开启" : "Brief: public picks enabled"}</span>
      </div>
      {plan === "pro" ? (
        <p className="rounded-md bg-panel px-3 py-2 text-sm font-semibold text-accent">{isZh ? "个性化早报已开启" : "Personalized brief enabled"}</p>
      ) : (
        <a className="secondary-button" href={`/${locale}/pricing`}>
          {isZh ? "查看 Pro 对比" : "Compare Pro"}
        </a>
      )}
    </aside>
  );
}
