"use client";

import { useEffect, useState } from "react";

const apiBase = process.env.NEXT_PUBLIC_READER_API_BASE ?? "http://127.0.0.1:8000";

type UsageDay = { day: string; count: number };

export function ApiUsageChart({ locale }: { locale: string }) {
  const [days, setDays] = useState<UsageDay[]>(Array.from({ length: 7 }, (_, index) => ({ day: `D-${6 - index}`, count: 0 })));
  const isZh = locale === "zh";

  useEffect(() => {
    const token = localStorage.getItem("codepick_token");
    const controller = new AbortController();
    fetch(`${apiBase}/api/api-keys/usage`, { headers: { Authorization: `Bearer ${token ?? ""}` }, signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("usage unavailable");
        return response.json();
      })
      .then((body) => setDays(body.days ?? []))
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

  const max = Math.max(1, ...days.map((day) => day.count));
  return (
    <section className="tool-panel">
      <h2 className="section-title">{isZh ? "近 7 天用量" : "Last 7 days usage"}</h2>
      <div className="usage-chart mt-4" aria-label={isZh ? "API 用量图表" : "API usage chart"}>
        {days.map((day) => (
          <div className="usage-bar-cell" key={day.day}>
            <div className="usage-bar" style={{ height: `${Math.max(6, (day.count / max) * 100)}%` }} />
            <span>{new Date(day.day).toLocaleDateString(isZh ? "zh-CN" : "en-US", { month: "numeric", day: "numeric" })}</span>
            <strong>{day.count}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}
