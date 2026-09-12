"use client";

import { useEffect, useState } from "react";

const apiBase = process.env.NEXT_PUBLIC_READER_API_BASE ?? "http://127.0.0.1:8000";

export function BriefGate({ locale }: { locale: string }) {
  const [plan, setPlan] = useState("free");
  const [status, setStatus] = useState("");

  useEffect(() => {
    const storedPlan = localStorage.getItem("codepick_plan") ?? "free";
    setPlan(storedPlan);
    if (storedPlan !== "pro") return;

    const controller = new AbortController();
    const token = localStorage.getItem("codepick_token");
    fetch(`${apiBase}/api/brief/me`, { headers: { Authorization: `Bearer ${token ?? ""}` }, signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("brief unavailable");
        setStatus(locale === "zh" ? "Pro \u4e2a\u4eba\u65e9\u62a5\u5df2\u540c\u6b65" : "Pro personal brief synced");
      })
      .catch(() => {
        setStatus(locale === "zh" ? "\u672c\u5730 Pro \u6f14\u793a\u65e9\u62a5\u5df2\u89e3\u9501" : "Local Pro demo brief unlocked");
      });

    return () => controller.abort();
  }, []);

  if (plan === "pro") {
    return (
      <p className="rounded-md border border-line bg-panel px-4 py-3 text-sm font-semibold text-accent">
        {status || (locale === "zh" ? "Pro \u4e2a\u4eba\u65e9\u62a5\u5df2\u89e3\u9501" : "Pro personal brief unlocked")}
      </p>
    );
  }

  return (
    <div className="rounded-md border border-line bg-panel px-4 py-3 text-sm text-muted">
      <p>{locale === "zh" ? "\u4e2a\u4eba\u65e9\u62a5\u9700\u8981 Pro\u3002\u5f53\u524d\u663e\u793a\u516c\u5171\u65e9\u62a5\u3002" : "Personal briefs require Pro. Showing the public brief."}</p>
      <a className="mt-2 inline-block font-bold text-ink" href={`/${locale}/login`}>
        {locale === "zh" ? "\u767b\u5f55\u6216\u5347\u7ea7" : "Sign in or upgrade"}
      </a>
    </div>
  );
}
