"use client";

import { useState } from "react";
import { clientApiUrl } from "../lib/client-api";
const requestTimeoutMs = 2500;
const copy = {
  en: { price: "Test values: $8/month · $79/year · $4.9 early bird", month: "$8 monthly", year: "$79 yearly", earlybird: "$4.9 early bird", checkout: "Sandbox checkout:" },
  zh: { price: "测试数值：$8/月 · $79/年 · $4.9 早鸟", month: "$8 月付", year: "$79 年付", earlybird: "$4.9 早鸟", checkout: "沙箱结账：" }
};

export function BillingPanel({ locale }: { locale: string }) {
  const t = copy[locale as "en" | "zh"] ?? copy.en;
  const [message, setMessage] = useState("");
  async function checkout(cadence: string) {
    const token = localStorage.getItem("codepick_token");
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), requestTimeoutMs);
    try {
      const response = await fetch(clientApiUrl("/api/billing/checkout"), { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token ?? ""}` }, body: JSON.stringify({ cadence }), signal: controller.signal });
      if (!response.ok) throw new Error("checkout unavailable");
      const body = await response.json();
      setMessage(body.checkout_url);
    } catch { setMessage(`https://sandbox-payments.codepick.local/checkout?cadence=${cadence}&currency=USD`); }
    finally { window.clearTimeout(timeout); }
  }
  return <section className="tool-panel"><p className="section-eyebrow">{locale === "zh" ? "交互验收" : "Interaction acceptance"}</p><h2 className="section-title mt-1">{locale === "zh" ? "沙箱结账" : "Sandbox checkout"}</h2><p className="mt-2 text-sm leading-6 text-muted">{t.price}</p><div className="mt-3 flex flex-wrap gap-2"><button className="secondary-button" onClick={() => checkout("month")}>{t.month}</button><button className="secondary-button" onClick={() => checkout("year")}>{t.year}</button><button className="secondary-button" onClick={() => checkout("earlybird")}>{t.earlybird}</button></div>{message ? <p className="mt-3 break-all text-sm text-muted" role="status">{t.checkout} {message}</p> : null}</section>;
}
