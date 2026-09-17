"use client";

import { useState } from "react";
import { ContentSummary, normalizeSort } from "../lib/api";
import { clientApiUrl } from "../lib/client-api";
import { ContentCard } from "./ContentCard";

const copy = {
  en: { load: "Load more", loading: "Loading…", retry: "Retry", error: "More items could not be loaded. Your current list is still available." },
  zh: { load: "加载更多", loading: "加载中…", retry: "重试", error: "暂时无法加载更多，当前列表仍可继续阅读。" }
};

function buildUrl(options: { vertical?: string; sort: string; cursor: string; query?: string }) {
  const url = new URL(clientApiUrl("/api/feed"), window.location.origin);
  if (options.vertical) url.searchParams.set("vertical", options.vertical);
  if (options.query) url.searchParams.set("q", options.query);
  url.searchParams.set("cursor", options.cursor);
  url.searchParams.set("sort", normalizeSort(options.sort) === "recommended" ? "score" : normalizeSort(options.sort));
  return url.toString();
}

export function LoadMore({ locale, initialCursor, vertical, sort, query }: {
  locale: string; initialCursor?: string | null; vertical?: string; sort: string; query?: string;
}) {
  const t = copy[locale as "en" | "zh"] ?? copy.en;
  const [cursor, setCursor] = useState(initialCursor ?? null);
  const [items, setItems] = useState<ContentSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadNext() {
    if (!cursor || loading) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch(buildUrl({ vertical, sort, cursor, query }));
      if (!response.ok) throw new Error("feed unavailable");
      const body = await response.json();
      setItems((current) => [...current, ...(body.items ?? [])]);
      setCursor(body.next_cursor ?? null);
    } catch {
      setError(t.error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-4">
      {items.map((item) => <ContentCard key={item.id} item={item} locale={locale} />)}
      {cursor ? <div className="load-more-row">
        <button className="secondary-button" type="button" onClick={loadNext} disabled={loading}>{loading ? t.loading : error ? t.retry : t.load}</button>
        {error ? <p className="text-sm font-semibold text-muted" role="status">{error}</p> : null}
      </div> : null}
    </div>
  );
}
