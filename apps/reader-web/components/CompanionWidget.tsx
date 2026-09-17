"use client";

import { FormEvent, useEffect, useState } from "react";
import { clientApiUrl } from "../lib/client-api";


const requestTimeoutMs = 2500;
function parseSseText(text: string) { return text.split(/\r?\n/).filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trimStart()).join(""); }
function quotaLabel(locale: string, quota: { used: number; limit: number; unlimited: boolean } | null) {
  if (!quota) return locale === "zh" ? "状态未知" : "Status unavailable";
  if (quota.unlimited) return locale === "zh" ? "测试 Pro · 无限" : "Test Pro · Unlimited";
  return `${Math.max(0, quota.limit - quota.used)}/${quota.limit}`;
}

export function CompanionWidget({ contentId, locale }: { contentId: string; locale: string }) {
  const isZh = locale === "zh";
  const [question, setQuestion] = useState(isZh ? "这篇文章的关键假设是什么？" : "What is the key assumption in this article?");
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; text: string }[]>([]);
  const [quota, setQuota] = useState<{ used: number; limit: number; unlimited: boolean } | null>(null);
  const [error, setError] = useState("");
  const [asking, setAsking] = useState(false);
  const prompts = isZh ? ["解释核心概念", "列出前提", "给出反例", "整理术语"] : ["Explain the core idea", "List assumptions", "Give a counterexample", "Define terms"];

  useEffect(() => {
    const token = localStorage.getItem("codepick_token");
    const controller = new AbortController();
    fetch(clientApiUrl("/api/companion/quota"), { headers: { Authorization: `Bearer ${token ?? ""}` }, signal: controller.signal })
      .then((response) => { if (!response.ok) throw new Error("quota unavailable"); return response.json(); })
      .then((body) => setQuota({ used: body.used ?? 0, limit: body.limit ?? 5, unlimited: body.unlimited === true }))
      .catch(() => setQuota(null));
    return () => controller.abort();
  }, []);

  async function submitQuestion(nextQuestion: string) {
    if (!nextQuestion.trim() || asking) return;
    setAsking(true); setError("");
    const token = localStorage.getItem("codepick_token");
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), requestTimeoutMs);
    try {
      const response = await fetch(clientApiUrl("/api/companion"), { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token ?? ""}` }, body: JSON.stringify({ content_id: contentId, question: nextQuestion }), signal: controller.signal });
      if (!response.ok) throw new Error("companion unavailable");
      const reader = response.body?.getReader();
      if (!reader) throw new Error("companion stream unavailable");
      setMessages((current) => [...current, { role: "user", text: nextQuestion }, { role: "assistant", text: "" }]);
      const unlimited = response.headers.get("X-Companion-Unlimited") === "true";
      const remaining = response.headers.get("X-Companion-Remaining");
      const limit = response.headers.get("X-Companion-Limit");
      if (unlimited && limit) setQuota({ used: 0, limit: Number(limit), unlimited: true });
      if (!unlimited && remaining && limit) setQuota({ used: Math.max(0, Number(limit) - Number(remaining)), limit: Number(limit), unlimited: false });
      const decoder = new TextDecoder();
      let buffered = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffered += decoder.decode(value, { stream: true });
        const nextAnswer = parseSseText(buffered).trim();
        setMessages((current) => current.map((message, index) => index === current.length - 1 ? { ...message, text: nextAnswer } : message));
      }
      buffered += decoder.decode();
      const finalAnswer = parseSseText(buffered).trim();
      setMessages((current) => current.map((message, index) => index === current.length - 1 ? { ...message, text: finalAnswer } : message));
    } catch {
      setError(isZh ? "伴读服务当前不可用，没有生成回答。可继续阅读原文或稍后重试。" : "The companion service is unavailable and no answer was generated. Continue with the source or retry later.");
    } finally { window.clearTimeout(timeout); setAsking(false); }
  }

  async function ask(event: FormEvent<HTMLFormElement>) { event.preventDefault(); await submitQuestion(question); }

  return <section className="tool-panel">
    <div className="flex items-center justify-between gap-3"><div><p className="section-eyebrow">{isZh ? "实验功能" : "Experimental"}</p><h2 className="section-title">{isZh ? "阅读伴侣" : "Reading companion"}</h2></div><span className="tag">{quotaLabel(locale, quota)}</span></div>
    <p className="mt-2 text-sm leading-6 text-muted">{isZh ? "回答来自当前配置的伴读服务；服务不可用时不会生成替代答案。" : "Answers come from the configured companion service. No substitute answer is invented when it is offline."}</p>
    <div className="mt-3 flex flex-wrap gap-2">{prompts.map((prompt) => <button className="chip" type="button" key={prompt} onClick={() => { setQuestion(prompt); void submitQuestion(prompt); }} disabled={asking}>{prompt}</button>)}</div>
    <form className="mt-3 flex flex-col gap-3 sm:flex-row" onSubmit={ask}><label className="sr-only" htmlFor={`companion-${contentId}`}>{isZh ? "伴读问题" : "Companion question"}</label><input id={`companion-${contentId}`} className="min-w-0 flex-1 rounded-md border border-line bg-white px-3 py-2 text-ink" value={question} onChange={(event) => setQuestion(event.target.value)} /><button className="primary-button" type="submit" disabled={asking}>{asking ? (isZh ? "提问中…" : "Asking…") : (isZh ? "提问" : "Ask")}</button></form>
    {error ? <p className="mt-3 rounded-md border border-line bg-panel p-3 text-sm leading-6 text-muted" role="alert">{error}</p> : null}
    {messages.length ? <div className="mt-4 grid gap-2" aria-live="polite">{messages.map((message, index) => <p className={message.role === "user" ? "rounded-md bg-panel p-3 text-sm font-semibold" : "rounded-md border border-line p-3 text-sm leading-6 text-muted"} key={index}>{message.text || (isZh ? "正在生成…" : "Generating…")}</p>)}</div> : null}
  </section>;
}
