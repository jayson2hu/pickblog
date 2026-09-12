"use client";

import { useState } from "react";
import { ContentSummary, normalizeSort } from "../lib/api";
import { ContentCard } from "./ContentCard";

const apiBase = process.env.NEXT_PUBLIC_READER_API_BASE ?? "http://127.0.0.1:8000";

const copy = {
  en: { load: "Load more", loading: "Loading", done: "No more picks", error: "Unable to load more right now." },
  zh: { load: "加载更多", loading: "加载中", done: "没有更多内容", error: "暂时无法加载更多。" }
};

function buildUrl(options: { vertical?: string; sort: string; cursor: string }) {
  const url = new URL(`${apiBase}/api/feed`);
  if (options.vertical) url.searchParams.set("vertical", options.vertical);
  url.searchParams.set("cursor", options.cursor);
  url.searchParams.set("sort", normalizeSort(options.sort) === "recommended" ? "score" : normalizeSort(options.sort));
  return url.toString();
}

export function LoadMore({
  locale,
  initialCursor,
  vertical,
  sort
}: {
  locale: string;
  initialCursor?: string | null;
  vertical?: string;
  sort: string;
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
      const response = await fetch(buildUrl({ vertical, sort, cursor }));
      if (!response.ok) throw new Error("feed unavailable");
      const body = await response.json();
      setItems((current) => [...current, ...(body.items ?? [])]);
      setCursor(body.next_cursor ?? null);
    } catch {
      setError(t.error);
      setCursor(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-4">
      {items.map((item) => (
        <ContentCard key={item.id} item={item} locale={locale} />
      ))}
      {cursor || error ? (
        <div className="load-more-row">
          <button className="secondary-button" type="button" onClick={loadNext} disabled={!cursor || loading}>
            {loading ? t.loading : cursor ? t.load : t.done}
          </button>
          {error ? <p className="text-sm font-semibold text-muted">{error}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
