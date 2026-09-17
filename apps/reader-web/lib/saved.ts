import type { ContentProvenance, ContentSummary } from "./api";

export type LocalSavedItem = {
  id: string; title: string; source: string; url: string; vertical: string;
  published_at: string | null; summary: string; provenance?: ContentProvenance; saved_at: string;
};

const idsKey = "cp_saved";
const itemsKey = "cp_saved_items";

function readJson<T>(key: string, fallback: T): T {
  try { return JSON.parse(localStorage.getItem(key) ?? "") as T; } catch { return fallback; }
}

export function readSavedItems(): LocalSavedItem[] {
  const items = readJson<LocalSavedItem[]>(itemsKey, []);
  const known = new Set(items.map((item) => item.id));
  const legacyIds = readJson<string[]>(idsKey, []);
  return [...items, ...legacyIds.filter((id) => !known.has(id)).map((id) => ({ id, title: id, source: "", url: "", vertical: "", published_at: null, summary: "", saved_at: "" }))];
}

export function savedSnapshot(item: ContentSummary): LocalSavedItem {
  return { id: item.id, title: item.title, source: item.source, url: item.url, vertical: item.vertical, published_at: item.published_at, summary: item.summary, provenance: item.provenance, saved_at: new Date().toISOString() };
}

export function setSaved(item: ContentSummary, saved: boolean) {
  const current = readSavedItems().filter((entry) => entry.id !== item.id);
  const next = saved ? [savedSnapshot(item), ...current] : current;
  localStorage.setItem(itemsKey, JSON.stringify(next));
  localStorage.setItem(idsKey, JSON.stringify(next.map((entry) => entry.id)));
  window.dispatchEvent(new CustomEvent("codepick:saved-change"));
}

export function hasSaved(contentId: string) {
  return readSavedItems().some((item) => item.id === contentId);
}
