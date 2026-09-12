"use client";

import { useState } from "react";

const apiBase = process.env.NEXT_PUBLIC_READER_API_BASE ?? "http://127.0.0.1:8000";
const requestTimeoutMs = 2500;
const copy = {
  en: { price: "$8/month / $79/year / early bird $4.9", month: "$8 monthly", year: "$79 yearly", earlybird: "$4.9 early bird", checkout: "Sandbox checkout:" },
  zh: { price: "$8/\u6708 / $79/\u5e74 / \u65e9\u9e1f $4.9", month: "$8 \u6708\u4ed8", year: "$79 \u5e74\u4ed8", earlybird: "$4.9 \u65e9\u9e1f", checkout: "\u6c99\u7bb1\u7ed3\u8d26\uff1a" }
};

export function BillingPanel({ locale }: { locale: string }) {
  const t = copy[locale as "en" | "zh"] ?? copy.en;
  const [message, setMessage] = useState("");

  async function checkout(cadence: string) {
    const token = localStorage.getItem("codepick_token");
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), requestTimeoutMs);
    try {
      const response = await fetch(`${apiBase}/api/billing/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token ?? ""}` },
        body: JSON.stringify({ cadence }),
        signal: controller.signal
      });
      if (!response.ok) throw new Error("checkout unavailable");
      const body = await response.json();
      setMessage(body.checkout_url);
    } catch {
      setMessage(`https://sandbox-payments.codepick.local/checkout?cadence=${cadence}&currency=USD`);
    } finally {
      window.clearTimeout(timeout);
    }
  }

  return (
    <section className="tool-panel">
      <h2 className="section-title">Pro</h2>
      <p className="mt-1 text-sm text-muted">{t.price}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button className="secondary-button" onClick={() => checkout("month")}>
          {t.month}
        </button>
        <button className="secondary-button" onClick={() => checkout("year")}>
          {t.year}
        </button>
        <button className="secondary-button" onClick={() => checkout("earlybird")}>
          {t.earlybird}
        </button>
      </div>
      {message ? (
        <p className="mt-3 break-all text-sm text-muted">
          {t.checkout} {message}
        </p>
      ) : null}
    </section>
  );
}
