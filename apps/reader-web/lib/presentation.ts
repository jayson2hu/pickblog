import type { ContentSummary } from "./api";

export function safeExternalUrl(value: string | undefined | null) {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? url.toString() : undefined;
  } catch {
    return undefined;
  }
}

export function sourceHost(item: Pick<ContentSummary, "url" | "source">) {
  const safeUrl = safeExternalUrl(item.url);
  if (safeUrl) return new URL(safeUrl).hostname.replace(/^www\./, "");
  if (item.url?.startsWith("file:")) return "local fixture";
  return item.source || "source unavailable";
}

export function formatPublishedDate(value: string | null | undefined, locale: string) {
  const date = value ? new Date(value) : undefined;
  if (!date || Number.isNaN(date.getTime())) return locale === "zh" ? "日期未知" : "Date unknown";
  return date.toLocaleDateString(locale === "zh" ? "zh-CN" : "en-US", { year: "numeric", month: "short", day: "numeric" });
}

export function readingMinutes(item: ContentSummary) {
  return Math.max(1, item.reading_minutes ?? item.read_time_minutes ?? 1);
}

export function provenanceLabels(item: ContentSummary, locale: string) {
  const isZh = locale === "zh";
  const provenance = item.provenance;
  const source = provenance?.source_kind === "public_feed" ? (isZh ? "公开来源" : "Public source") : provenance?.source_kind === "fixture" ? (isZh ? "测试样例" : "Fixture") : (isZh ? "来源待确认" : "Source unverified");
  const scoring = provenance?.scoring_method === "heuristic" ? (isZh ? "规则分析" : "Rule analysis") : provenance?.scoring_method === "simulated" ? (isZh ? "模拟评分" : "Simulated scoring") : provenance?.scoring_method === "model" ? (isZh ? "模型分析" : "Model analysis") : (isZh ? "分析方法未知" : "Method unknown");
  const review = provenance?.reviewed ? (isZh ? "已人工复核" : "Human reviewed") : (isZh ? "未人工复核" : "Not human reviewed");
  return [source, scoring, review];
}
