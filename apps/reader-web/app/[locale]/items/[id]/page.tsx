import { Metadata } from "next";
import { notFound } from "next/navigation";
import { BilingualBody } from "../../../../components/BilingualBody";
import { CompanionWidget } from "../../../../components/CompanionWidget";
import { CoverThumb } from "../../../../components/CoverThumb";
import { ProvenanceStrip } from "../../../../components/ProvenanceStrip";
import { ReadingActions } from "../../../../components/ReadingActions";
import { SaveLaterButton } from "../../../../components/SaveLaterButton";
import { ScoreExplainer } from "../../../../components/ScoreExplainer";
import { getItem } from "../../../../lib/api";
import { formatPublishedDate, readingMinutes, safeExternalUrl, sourceHost } from "../../../../lib/presentation";

type Props = { params: Promise<{ locale: string; id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, id } = await params;
  const item = await getItem(id);
  if (!item) return {};
  const translationAvailable = item.provenance?.translation_available === true && Boolean(item.translations?.zh);
  const title = locale === "zh" && translationAvailable ? item.translations.zh.title : item.title;
  const sourceUrl = safeExternalUrl(item.provenance?.source_url ?? item.url);
  return { title: `${title} | CodePick`, description: item.summary, alternates: { languages: { en: `/en/items/${item.id}`, zh: `/zh/items/${item.id}` } }, openGraph: { title, description: item.summary, ...(sourceUrl ? { url: sourceUrl } : {}) } };
}

export default async function ItemPage({ params }: Props) {
  const { locale, id } = await params;
  const item = await getItem(id);
  if (!item) notFound();
  const isZh = locale === "zh";
  const translated = item.provenance?.translation_available === true ? item.translations?.zh : undefined;
  const title = isZh && translated ? translated.title : item.title;
  const summary = isZh && translated ? translated.base_analysis.summary : item.base_analysis.summary;
  const viewpoints = isZh && translated ? translated.base_analysis.viewpoints : item.base_analysis.viewpoints;
  const quotes = isZh && translated ? translated.base_analysis.quotes : item.base_analysis.quotes;
  const sourceUrl = safeExternalUrl(item.provenance?.source_url ?? item.url);
  const schema = { "@context": "https://schema.org", "@type": "Article", headline: title, ...(sourceUrl ? { url: sourceUrl } : {}), ...(item.published_at ? { datePublished: item.published_at } : {}) };

  return <article className="article-page">
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />
    <a className="back-link" href={`/${locale}`}>← {isZh ? "返回今日精选" : "Back to today’s picks"}</a>
    <header className="article-header">
      <div className="article-lead">
        <div className="source-line">{sourceUrl ? <a href={sourceUrl} target="_blank" rel="noopener noreferrer">{item.source || sourceHost(item)}</a> : <span>{item.source || sourceHost(item)}</span>}<span>·</span><span>{sourceHost(item)}</span><span>·</span><span>{formatPublishedDate(item.published_at, locale)}</span><span>·</span><span>{readingMinutes(item)} {isZh ? "分钟" : "min"}</span></div>
        <ProvenanceStrip item={item} locale={locale} />
        <h1 className="article-title">{title}</h1>
        <div className="analysis-summary"><p className="section-eyebrow">{isZh ? "自动摘要" : "Automated summary"}</p><p>{summary}</p></div>
        <div className="article-actions">{sourceUrl ? <a className="primary-button" href={sourceUrl} target="_blank" rel="noopener noreferrer">{isZh ? "打开发布者原文" : "Open publisher source"}</a> : <span className="tag">{isZh ? "来源链接不可用" : "Source link unavailable"}</span>}<SaveLaterButton item={item} locale={locale} /></div>
      </div>
      <aside className="article-aside"><CoverThumb source={item.source} vertical={item.vertical} thumbnail={item.thumbnail} /><div className="trust-note"><p className="metric-label">{isZh ? "阅读提示" : "Reading note"}</p><p>{isZh ? "先用来源链接核对上下文，再把自动摘要和排序信号作为阅读辅助。" : "Verify context at the source, then use the automated summary and ranking signals as reading aids."}</p></div></aside>
    </header>
    <BilingualBody item={item} locale={locale} />
    <section className="reading-section">
      <div className="section-heading-row"><div><p className="section-eyebrow">{isZh ? "自动生成" : "Automated output"}</p><h2 className="section-title">{isZh ? "分析笔记" : "Analysis notes"}</h2></div><span className="tag">{item.provenance?.reviewed ? (isZh ? "已人工复核" : "Human reviewed") : (isZh ? "未人工复核" : "Not human reviewed")}</span></div>
      {viewpoints.length ? <ol className="analysis-list">{viewpoints.map((point, index) => <li key={`${point}-${index}`}><span>{String(index + 1).padStart(2, "0")}</span><p>{point}</p></li>)}</ol> : <p className="empty-inline">{isZh ? "当前没有可展示的分析观点。" : "No analysis viewpoints are stored for this item."}</p>}
      {quotes[0] ? <blockquote className="analysis-quote"><span>{isZh ? "分析摘记" : "Analysis highlight"}</span>{quotes[0]}</blockquote> : null}
    </section>
    <ScoreExplainer scores={item.scores} locale={locale} method={item.provenance?.scoring_method} />
    <div className="article-tools"><ReadingActions contentId={item.id} locale={locale} /><CompanionWidget contentId={item.id} locale={locale} /></div>
  </article>;
}
