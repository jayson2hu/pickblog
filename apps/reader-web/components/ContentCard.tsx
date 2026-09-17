import { ContentSummary } from "../lib/api";
import { formatPublishedDate, readingMinutes, safeExternalUrl, sourceHost } from "../lib/presentation";
import { CoverThumb } from "./CoverThumb";
import { ProvenanceStrip } from "./ProvenanceStrip";
import { SaveLaterButton } from "./SaveLaterButton";
import { TrackedContentLink } from "./TrackedContentLink";

export function ContentCard({ item, locale, featured = false }: { item: ContentSummary; locale: string; featured?: boolean }) {
  const isZh = locale === "zh";
  const sourceUrl = safeExternalUrl(item.url);
  return (
    <article className={featured ? "content-card featured-card" : "content-card"}>
      <CoverThumb source={item.source} vertical={item.vertical} thumbnail={item.thumbnail} />
      <div className="grid min-w-0 gap-3">
        <div className="source-line">
          {sourceUrl ? <a href={sourceUrl} target="_blank" rel="noopener noreferrer">{sourceHost(item)}</a> : <span>{sourceHost(item)}</span>}
          <span>·</span><span>{formatPublishedDate(item.published_at, locale)}</span>
          <span>·</span><span>{readingMinutes(item)} {isZh ? "分钟" : "min"}</span>
        </div>
        <h2 className={featured ? "text-3xl font-bold leading-tight tracking-normal" : "text-2xl font-bold leading-tight tracking-normal"}>
          <TrackedContentLink contentId={item.id} href={`/${locale}/items/${item.id}`}>{item.title}</TrackedContentLink>
        </h2>
        <p className="max-w-3xl text-base leading-7 text-muted">{item.summary}</p>
        {item.tags?.length ? <div className="flex flex-wrap gap-2" aria-label={isZh ? "内容标签" : "Content tags"}>{item.tags.slice(0, 4).map((tag) => <span className="tag" key={tag}>{tag}</span>)}</div> : null}
        <p className="reason-line"><span className="reason-label">{isZh ? "入队依据" : "Queue rationale"}</span>{item.reason?.[locale as "en" | "zh"] ?? item.reason?.en}</p>
        <div className="card-footer"><ProvenanceStrip item={item} locale={locale} compact /><SaveLaterButton item={item} locale={locale} /></div>
      </div>
    </article>
  );
}
