"use client";

import { useState } from "react";

const apiBase = process.env.NEXT_PUBLIC_READER_API_BASE ?? "http://127.0.0.1:8000";

const copy = {
  en: {
    deepRead: "Mark deep read",
    bookmark: "Bookmark",
    notInterested: "Not interested",
    deepReadSaved: "Deep read saved",
    bookmarkSaved: "Bookmark saved",
    notInterestedSaved: "Preference saved",
    localDeepReadSaved: "Local deep read saved",
    localBookmarkSaved: "Local bookmark saved",
    localNotInterestedSaved: "Local preference saved",
    signInRequired: "Sign in required"
  },
  zh: {
    deepRead: "\u6807\u8bb0\u6df1\u8bfb",
    bookmark: "\u6536\u85cf",
    notInterested: "\u4e0d\u611f\u5174\u8da3",
    deepReadSaved: "\u6df1\u8bfb\u5df2\u8bb0\u5f55",
    bookmarkSaved: "\u6536\u85cf\u5df2\u4fdd\u5b58",
    notInterestedSaved: "\u504f\u597d\u5df2\u4fdd\u5b58",
    localDeepReadSaved: "\u672c\u5730\u6df1\u8bfb\u5df2\u8bb0\u5f55",
    localBookmarkSaved: "\u672c\u5730\u6536\u85cf\u5df2\u4fdd\u5b58",
    localNotInterestedSaved: "\u672c\u5730\u504f\u597d\u5df2\u4fdd\u5b58",
    signInRequired: "\u9700\u8981\u767b\u5f55"
  }
};

export function ReadingActions({ contentId, locale }: { contentId: string; locale: string }) {
  const t = copy[locale as "en" | "zh"] ?? copy.en;
  const [status, setStatus] = useState("");

  async function postJson(path: string, body: Record<string, unknown>, fallbackStatus: string, successStatus: string) {
    const token = localStorage.getItem("codepick_token");
    try {
      const response = await fetch(`${apiBase}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token ?? ""}` },
        body: JSON.stringify(body)
      });
      if (response.status === 401 || response.status === 403) {
        setStatus(t.signInRequired);
        return;
      }
      if (!response.ok) throw new Error("request failed");
      setStatus(successStatus);
    } catch {
      setStatus(fallbackStatus);
    }
  }

  return (
    <section className="tool-panel">
      <h2 className="section-title">{locale === "zh" ? "\u9605\u8bfb\u52a8\u4f5c" : "Reading actions"}</h2>
      <div className="flex flex-wrap gap-3">
        <button
          className="secondary-button"
          onClick={() => postJson("/api/events", { content_id: contentId, type: "deep_read" }, t.localDeepReadSaved, t.deepReadSaved)}
        >
          {t.deepRead}
        </button>
        <button
          className="secondary-button"
          onClick={() => postJson("/api/bookmarks", { content_id: contentId, note: "saved from reader", highlights: [] }, t.localBookmarkSaved, t.bookmarkSaved)}
        >
          {t.bookmark}
        </button>
        <button
          className="secondary-button"
          onClick={() => postJson("/api/events", { content_id: contentId, type: "not_interested" }, t.localNotInterestedSaved, t.notInterestedSaved)}
        >
          {t.notInterested}
        </button>
      </div>
      {status ? <p className="mt-3 text-sm text-accent">{status}</p> : null}
    </section>
  );
}
