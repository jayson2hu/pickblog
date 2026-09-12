import { ContentSummary } from "../lib/api";
import { CoverThumb } from "./CoverThumb";
import { SaveLaterButton } from "./SaveLaterButton";
import { TrackedContentLink } from "./TrackedContentLink";

export function ContentCard({ item, locale, featured = false }: { item: ContentSummary; locale: string; featured?: boolean }) {
  return (
    <article className={featured ? "content-card featured-card" : "content-card"}>
      <CoverThumb source={item.source} vertical={item.vertical} thumbnail={item.thumbnail} />
      <div className="grid min-w-0 gap-3">
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted">
          <span className="tag">{item.source}</span>
          <span className="tag">{item.vertical}</span>
          <span className="tag">{item.read_time_minutes ?? 1} min</span>
          <span className="tag">{new Date(item.published_at).toLocaleDateString(locale === "zh" ? "zh-CN" : "en-US")}</span>
        </div>
        <h2 className={featured ? "text-3xl font-bold leading-tight tracking-normal" : "text-2xl font-bold leading-tight tracking-normal"}>
          <TrackedContentLink contentId={item.id} href={`/${locale}/items/${item.id}`}>
            {item.title}
          </TrackedContentLink>
        </h2>
        <p className="max-w-3xl text-base leading-7 text-muted">{item.summary}</p>
        <p className="reason-line">{item.reason?.[locale as "en" | "zh"] ?? item.reason?.en ?? (locale === "zh" ? "质量分与影响力靠前，适合纳入今日阅读。" : "High signal and impact make this a useful read today.")}</p>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="score-pill" aria-label={locale === "zh" ? "质量分" : "Quality score"}>
            <span>{item.scores.quality}</span>
            <small>{locale === "zh" ? "质量" : "Quality"}</small>
          </div>
          <SaveLaterButton contentId={item.id} locale={locale} />
        </div>
      </div>
    </article>
  );
}
