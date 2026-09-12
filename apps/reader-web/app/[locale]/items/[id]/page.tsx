import { BilingualBody } from "../../../../components/BilingualBody";
import { Metadata } from "next";
import { notFound } from "next/navigation";
import { CompanionWidget } from "../../../../components/CompanionWidget";
import { CoverThumb } from "../../../../components/CoverThumb";
import { ReadingActions } from "../../../../components/ReadingActions";
import { ScoreExplainer } from "../../../../components/ScoreExplainer";
import { getItem } from "../../../../lib/api";

type Props = { params: { locale: string; id: string } };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const item = await getItem(params.id);
  if (!item) return {};
  const title = params.locale === "zh" ? item.translations.zh?.title ?? item.title : item.title;
  return {
    title: `${title} | CodePick`,
    description: item.summary,
    alternates: { languages: { en: `/en/items/${item.id}`, zh: `/zh/items/${item.id}` } },
    openGraph: { title, description: item.summary, url: item.url }
  };
}

export default async function ItemPage({ params }: Props) {
  const item = await getItem(params.id);
  if (!item) notFound();
  const translated = params.locale === "zh" ? item.translations.zh : undefined;
  const title = translated?.title ?? item.title;
  const summary = translated?.base_analysis.summary ?? item.base_analysis.summary;
  const viewpoints = translated?.base_analysis.viewpoints ?? item.base_analysis.viewpoints;
  const quotes = translated?.base_analysis.quotes ?? item.base_analysis.quotes;
  const localeDate = new Date(item.published_at).toLocaleDateString(params.locale === "zh" ? "zh-CN" : "en-US");

  return (
    <article className="grid gap-8">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({ "@context": "https://schema.org", "@type": "Article", headline: title, datePublished: item.published_at })
        }}
      />
      <header className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <div>
          <div className="flex flex-wrap gap-2">
            <span className="tag">{item.source}</span>
            <span className="tag">{item.vertical}</span>
            <span className="tag">{item.read_time_minutes ?? 1} min</span>
            <span className="tag">{localeDate}</span>
          </div>
          <h1 className="page-title">{title}</h1>
          <p className="page-subtitle">{summary}</p>
          <div className="mt-5 flex flex-wrap gap-3">
            <a className="primary-button" href={item.url} target="_blank" rel="noopener noreferrer">
              {params.locale === "zh" ? "\u6253\u5f00\u539f\u6587" : "Open original"}
            </a>
            <a className="secondary-button" href={`/${params.locale}/pricing`}>
              {params.locale === "zh" ? "\u67e5\u770b Pro" : "Compare Pro"}
            </a>
          </div>
        </div>
        <aside className="self-start">
          <CoverThumb source={item.source} vertical={item.vertical} thumbnail={item.thumbnail} />
          <div className="tool-panel mt-4">
            <p className="metric-label">{params.locale === "zh" ? "\u5165\u9009\u7406\u7531" : "Why this was picked"}</p>
            <p className="mt-2 text-sm leading-6 text-muted">{item.reason?.[params.locale as "en" | "zh"] ?? item.reason?.en}</p>
          </div>
        </aside>
      </header>

      <ScoreExplainer scores={item.scores} locale={params.locale} />
      <BilingualBody item={item} locale={params.locale} />

      <section className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <div className="tool-panel">
          <h2 className="section-title">{params.locale === "zh" ? "\u89c2\u70b9" : "Viewpoints"}</h2>
          <ul className="mt-4 grid gap-3">
            {viewpoints.map((point, index) => (
              <li key={point} className="flex gap-3 rounded-md bg-panel p-3 text-muted">
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-white text-xs font-bold text-ink">{index + 1}</span>
                <span className="leading-7">{point}</span>
              </li>
            ))}
          </ul>
        </div>
        <blockquote className="tool-panel border-l-4 border-l-accent text-lg font-semibold leading-8 text-ink">{quotes[0]}</blockquote>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <ReadingActions contentId={item.id} locale={params.locale} />
        <CompanionWidget contentId={item.id} locale={params.locale} />
      </div>
    </article>
  );
}
