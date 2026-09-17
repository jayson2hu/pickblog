"use client";

import { useState } from "react";
import { clientApiUrl } from "../lib/client-api";


const copy = {
  en: { deepRead: "Mark as read", bookmark: "Save to account", notInterested: "Less like this", deepReadSaved: "Read status saved to your account.", bookmarkSaved: "Saved to your account.", notInterestedSaved: "Preference saved to your account.", requestFailed: "The account service did not confirm this action. Nothing was reported as saved.", signInRequired: "Use a development session to save account actions. You can still use Save for later on this device." },
  zh: { deepRead: "标记已读", bookmark: "保存到账户", notInterested: "减少此类内容", deepReadSaved: "已将阅读状态保存到账户。", bookmarkSaved: "已保存到账户。", notInterestedSaved: "已将偏好保存到账户。", requestFailed: "账户服务未确认此操作，本次没有显示为已保存。", signInRequired: "请先使用开发会话保存账户动作；你仍可使用本机“稍后读”。" }
};

export function ReadingActions({ contentId, locale }: { contentId: string; locale: string }) {
  const t = copy[locale as "en" | "zh"] ?? copy.en;
  const [status, setStatus] = useState("");

  async function postJson(path: string, body: Record<string, unknown>, successStatus: string) {
    const token = localStorage.getItem("codepick_token");
    if (!token) { setStatus(t.signInRequired); return; }
    setStatus("");
    try {
      const response = await fetch(clientApiUrl(path), { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify(body) });
      if (response.status === 401 || response.status === 403) { setStatus(t.signInRequired); return; }
      if (!response.ok) throw new Error("request failed");
      setStatus(successStatus);
    } catch { setStatus(t.requestFailed); }
  }

  return <section className="tool-panel">
    <div><p className="section-eyebrow">{locale === "zh" ? "账户动作" : "Account actions"}</p><h2 className="section-title">{locale === "zh" ? "同步阅读状态" : "Sync reading state"}</h2><p className="mt-2 text-sm leading-6 text-muted">{locale === "zh" ? "以下动作只在服务端确认后显示成功。" : "These actions only report success after the account service confirms them."}</p></div>
    <div className="mt-4 flex flex-wrap gap-3">
      <button className="secondary-button" type="button" onClick={() => postJson("/api/events", { content_id: contentId, type: "deep_read" }, t.deepReadSaved)}>{t.deepRead}</button>
      <button className="secondary-button" type="button" onClick={() => postJson("/api/bookmarks", { content_id: contentId, note: "saved from reader", highlights: [] }, t.bookmarkSaved)}>{t.bookmark}</button>
      <button className="secondary-button" type="button" onClick={() => postJson("/api/events", { content_id: contentId, type: "not_interested" }, t.notInterestedSaved)}>{t.notInterested}</button>
    </div>
    {status ? <p className="mt-3 text-sm text-accent" role="status">{status}</p> : null}
  </section>;
}
