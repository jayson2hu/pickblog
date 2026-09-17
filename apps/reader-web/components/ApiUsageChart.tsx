"use client";

import { useEffect, useState } from "react";
import { clientApiUrl } from "../lib/client-api";
type UsageDay = { day: string; count: number };

export function ApiUsageChart({ locale }: { locale: string }) {
  const [days, setDays] = useState<UsageDay[] | null>(null);
  const isZh = locale === "zh";
  useEffect(() => {
    const token = localStorage.getItem("codepick_token");
    const controller = new AbortController();
    fetch(clientApiUrl("/api/api-keys/usage"), { headers: { Authorization: `Bearer ${token ?? ""}` }, signal: controller.signal })
      .then((response) => { if (!response.ok) throw new Error("usage unavailable"); return response.json(); })
      .then((body) => setDays(body.days ?? []))
      .catch(() => setDays([]));
    return () => controller.abort();
  }, []);

  const validDays = (days ?? []).filter((day) => !Number.isNaN(new Date(day.day).getTime()));
  const max = Math.max(1, ...validDays.map((day) => day.count));
  return <section className="tool-panel"><h2 className="section-title">{isZh ? "近 7 天用量" : "Last 7 days usage"}</h2>
    {days === null ? <p className="empty-inline">{isZh ? "正在读取用量…" : "Loading usage…"}</p> : validDays.length ? <div className="usage-chart mt-4" aria-label={isZh ? "API 用量图表" : "API usage chart"}>{validDays.map((day) => <div className="usage-bar-cell" key={day.day}><div className="usage-bar" style={{ height: `${Math.max(6, (day.count / max) * 100)}%` }} /><span>{new Date(day.day).toLocaleDateString(isZh ? "zh-CN" : "en-US", { month: "numeric", day: "numeric" })}</span><strong>{day.count}</strong></div>)}</div> : <p className="empty-inline">{isZh ? "没有可验证的 API 用量记录。" : "No verified API usage records are available."}</p>}
  </section>;
}
