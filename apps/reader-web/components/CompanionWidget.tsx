"use client";

import { FormEvent, useEffect, useState } from "react";

const apiBase = process.env.NEXT_PUBLIC_READER_API_BASE ?? "http://127.0.0.1:8000";
const requestTimeoutMs = 2500;

function parseSseText(text: string) {
  return text
    .split(/\r?\n/)
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("");
}

function quotaLabel(locale: string, quota: { used: number; limit: number; unlimited: boolean } | null) {
  if (!quota) return "Free: 5/day";
  if (quota.unlimited) return locale === "zh" ? "Pro · 无限" : "Pro · Unlimited";
  return `${Math.max(0, quota.limit - quota.used)}/${quota.limit}`;
}

export function CompanionWidget({ contentId, locale }: { contentId: string; locale: string }) {
  const defaultQuestion = locale === "zh" ? "这篇值得深读吗？" : "Is this worth a deep read?";
  const [question, setQuestion] = useState(defaultQuestion);
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; text: string }[]>([]);
  const [quota, setQuota] = useState<{ used: number; limit: number; unlimited: boolean } | null>(null);
  const latestAnswer = [...messages].reverse().find((message) => message.role === "assistant")?.text ?? "";
  const prompts = locale === "zh" ? ["用更简单的话说", "给我背景", "术语表", "横向对比"] : ["Explain simply", "Give background", "Terminology", "Compare options"];

  useEffect(() => {
    const token = localStorage.getItem("codepick_token");
    const controller = new AbortController();
    fetch(`${apiBase}/api/companion/quota`, { headers: { Authorization: `Bearer ${token ?? ""}` }, signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("quota unavailable");
        return response.json();
      })
      .then((body) => setQuota({ used: body.used ?? 0, limit: body.limit ?? 5, unlimited: body.unlimited === true }))
      .catch(() => setQuota(null));
    return () => controller.abort();
  }, []);

  async function submitQuestion(nextQuestion: string) {
    const token = localStorage.getItem("codepick_token");
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), requestTimeoutMs);
    try {
      const response = await fetch(`${apiBase}/api/companion`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token ?? ""}` },
        body: JSON.stringify({ content_id: contentId, question: nextQuestion }),
        signal: controller.signal
      });
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
        const next = parseSseText(buffered).trim();
        setMessages((current) => current.map((message, index) => (index === current.length - 1 ? { ...message, text: next } : message)));
      }
      buffered += decoder.decode();
      const finalAnswer = parseSseText(buffered).trim();
      setMessages((current) => current.map((message, index) => (index === current.length - 1 ? { ...message, text: finalAnswer } : message)));
    } catch {
      const fallback =
        locale === "zh"
          ? "本地伴读建议：先看质量分、观点和金句，再决定是否深读。"
          : "Local companion: check quality score, viewpoints, and quote before deciding to deep read.";
      setMessages((current) => [...current, { role: "user", text: nextQuestion }, { role: "assistant", text: fallback }]);
    } finally {
      window.clearTimeout(timeout);
    }
  }

  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await submitQuestion(question);
  }

  return (
    <section className="tool-panel">
      <div className="flex items-center justify-between gap-3">
        <h2 className="section-title">{locale === "zh" ? "AI 伴读" : "AI companion"}</h2>
        <span className="tag">{quotaLabel(locale, quota)}</span>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {prompts.map((prompt) => (
          <button
            className="chip"
            type="button"
            key={prompt}
            onClick={() => {
              setQuestion(prompt);
              void submitQuestion(prompt);
            }}
          >
            {prompt}
          </button>
        ))}
      </div>
      <form className="mt-3 flex flex-col gap-3 sm:flex-row" onSubmit={ask}>
        <input className="min-w-0 flex-1 rounded-md border border-line bg-white px-3 py-2 text-ink" value={question} onChange={(event) => setQuestion(event.target.value)} />
        <button className="primary-button" type="submit">
          {locale === "zh" ? "提问" : "Ask"}
        </button>
      </form>
      {messages.length ? (
        <div className="mt-4 grid gap-2">
          {messages.map((message, index) => (
            <p className={message.role === "user" ? "rounded-md bg-panel p-3 text-sm font-semibold" : "rounded-md border border-line p-3 text-sm leading-6 text-muted"} key={index}>
              {message.text || latestAnswer}
            </p>
          ))}
        </div>
      ) : null}
    </section>
  );
}
