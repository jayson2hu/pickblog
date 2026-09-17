"use client";

import { useEffect, useState } from "react";
import { clientApiUrl } from "../lib/client-api";


export function BriefGate({ locale }: { locale: string }) {
  const [plan, setPlan] = useState("free");
  const [status, setStatus] = useState("");
  useEffect(() => {
    const storedPlan = localStorage.getItem("codepick_plan") ?? "free";
    setPlan(storedPlan);
    if (storedPlan !== "pro") return;
    const controller = new AbortController();
    const token = localStorage.getItem("codepick_token");
    fetch(clientApiUrl("/api/brief/me"), { headers: { Authorization: `Bearer ${token ?? ""}` }, signal: controller.signal })
      .then((response) => { if (!response.ok) throw new Error("brief unavailable"); setStatus(locale === "zh" ? "个人早报接口已确认" : "Personal brief confirmed by the API"); })
      .catch(() => setStatus(locale === "zh" ? "本机 Pro 测试标记已开启；个人早报接口不可用" : "Local Pro test flag is active; the personal brief API is unavailable"));
    return () => controller.abort();
  }, [locale]);

  if (plan === "pro") return <p className="environment-notice" role="status">{status || (locale === "zh" ? "正在核对个人早报接口…" : "Checking the personal brief API…")}</p>;
  return <div className="environment-notice"><p>{locale === "zh" ? "当前显示公共清单。个人早报仍是待验证能力。" : "Showing the public list. Personal briefs remain a capability to validate."}</p><a className="mt-2 inline-block font-bold text-ink" href={`/${locale}/login`}>{locale === "zh" ? "打开本机会话" : "Open local session"}</a></div>;
}
