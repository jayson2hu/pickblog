"use client";

import { useEffect, useState } from "react";
import { formatPublishedDate, safeExternalUrl, sourceHost } from "../lib/presentation";
import { LocalSavedItem, readSavedItems } from "../lib/saved";

export function SavedLibrary({ locale }: { locale: string }) {
  const [items, setItems] = useState<LocalSavedItem[] | null>(null);
  const isZh = locale === "zh";
  useEffect(() => {
    const refresh = () => setItems(readSavedItems());
    refresh();
    window.addEventListener("storage", refresh);
    window.addEventListener("codepick:saved-change", refresh);
    return () => { window.removeEventListener("storage", refresh); window.removeEventListener("codepick:saved-change", refresh); };
  }, []);

  function remove(contentId: string) {
    const next = readSavedItems().filter((item) => item.id !== contentId);
    localStorage.setItem("cp_saved_items", JSON.stringify(next));
    localStorage.setItem("cp_saved", JSON.stringify(next.map((item) => item.id)));
    window.dispatchEvent(new CustomEvent("codepick:saved-change"));
  }

  if (items === null) return <p className="state-panel" aria-live="polite">{isZh ? "正在读取本机收藏…" : "Loading local saves…"}</p>;
  if (!items.length) return <section className="state-panel text-center">
    <p className="page-kicker">{isZh ? "收藏为空" : "Nothing saved yet"}</p>
    <h2 className="section-title mt-2">{isZh ? "先从今日精选保存一篇" : "Save a useful piece from today’s picks"}</h2>
    <p className="mt-3 text-sm leading-6 text-muted">{isZh ? "游客收藏保存在当前浏览器。登录后的账户收藏只有在服务端确认成功后才会显示成功。" : "Guest saves stay in this browser. Account bookmarks only report success after the server confirms them."}</p>
    <a className="primary-button mt-5" href={`/${locale}`}>{isZh ? "浏览今日精选" : "Browse today’s picks"}</a>
  </section>;

  return <div className="saved-list">{items.map((item) => {
    const sourceUrl = safeExternalUrl(item.url);
    return <article className="saved-card" key={item.id}>
      <div className="min-w-0">
        <div className="flex flex-wrap gap-2 text-xs text-muted"><span>{item.source || (isZh ? "来源待加载" : "Source unavailable")}</span>{item.published_at ? <span>· {formatPublishedDate(item.published_at, locale)}</span> : null}<span>· {sourceHost(item)}</span></div>
        <h2 className="mt-2 text-xl font-bold leading-snug"><a href={`/${locale}/items/${item.id}`}>{item.title}</a></h2>
        {item.summary ? <p className="mt-2 line-clamp-2 text-sm leading-6 text-muted">{item.summary}</p> : null}
      </div>
      <div className="saved-actions">
        <a className="secondary-button" href={`/${locale}/items/${item.id}`}>{isZh ? "查看分析" : "View analysis"}</a>
        {sourceUrl ? <a className="secondary-button" href={sourceUrl} target="_blank" rel="noopener noreferrer">{isZh ? "打开原文" : "Open source"}</a> : null}
        <button className="text-button" type="button" onClick={() => remove(item.id)}>{isZh ? "移除" : "Remove"}</button>
      </div>
    </article>;
  })}</div>;
}
