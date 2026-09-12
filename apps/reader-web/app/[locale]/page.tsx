import { ContentCard } from "../../components/ContentCard";
import { DismissibleHero } from "../../components/DismissibleHero";
import { FeedFilters } from "../../components/FeedFilters";
import { LoadMore } from "../../components/LoadMore";
import { Sidebar } from "../../components/Sidebar";
import { TrackedContentLink } from "../../components/TrackedContentLink";
import { getFeedPage, normalizeSort } from "../../lib/api";
import { fallbackTaxonomyFromFeed, getTaxonomy } from "../../lib/taxonomy";

const copy = {
  en: {
    title: "Public picks",
    subtitle: "High-signal completed content, ranked for focused engineering reading.",
    kicker: "Reader Web",
    heroTitle: "Read the few pieces that change a decision",
    heroText: "CodePick turns completed L2 judgments into a calm reading queue with reasons, read time, and save-later flow.",
    how: "How scoring works",
    scoreExplainer: "Six-dimension scores come from L2. L3 reads them and derives read time and display reasons.",
    featured: "Featured",
    empty: "No public picks match this filter yet."
  },
  zh: {
    title: "公共精选",
    subtitle: "面向工程阅读的高信号 COMPLETED 内容。",
    kicker: "阅读器",
    heroTitle: "只读对决策有帮助的那几篇",
    heroText: "CodePick 把 L2 完成的判断转成安静的阅读队列，附带入选理由、读时和稍后读。",
    how: "如何评分",
    scoreExplainer: "六维评分来自 L2。L3 只读评分，并派生阅读时长与展示理由。",
    featured: "头条精选",
    empty: "当前筛选下还没有公开精选内容。"
  }
};

export default async function Home({
  params,
  searchParams
}: {
  params: { locale: string };
  searchParams?: { vertical?: string; sort?: string };
}) {
  const t = copy[params.locale as "en" | "zh"] ?? copy.en;
  const currentSort = normalizeSort(searchParams?.sort);
  const currentVertical = searchParams?.vertical;
  const page = await getFeedPage({ vertical: currentVertical, sort: currentSort });
  const items = page.items;
  const taxonomy = (await getTaxonomy(params.locale)) ?? fallbackTaxonomyFromFeed(items, params.locale);
  const top = items[0];
  const rest = items.slice(1);

  return (
    <section className="grid gap-8">
      <DismissibleHero locale={params.locale}>
        <div className="hero-band grid gap-6 lg:grid-cols-[1fr_320px] lg:items-end">
          <div>
            <p className="page-kicker">{t.kicker}</p>
            <h1 className="page-title">{t.title}</h1>
            <p className="page-subtitle">{t.subtitle}</p>
            <h2 className="mt-6 text-2xl font-bold tracking-normal">{t.heroTitle}</h2>
            <p className="mt-2 max-w-2xl text-base leading-7 text-muted">{t.heroText}</p>
            <details className="mt-4 text-sm text-muted">
              <summary className="cursor-pointer font-bold text-ink">{t.how}</summary>
              <p className="mt-2">{t.scoreExplainer}</p>
            </details>
          </div>
          {top ? (
            <div className="tool-panel">
              <p className="metric-label">{t.featured}</p>
              <h2 className="mt-2 text-xl font-bold tracking-normal">
                <TrackedContentLink contentId={top.id} href={`/${params.locale}/items/${top.id}`}>
                  {top.title}
                </TrackedContentLink>
              </h2>
              <p className="mt-3 text-sm leading-6 text-muted">{top.reason?.[params.locale as "en" | "zh"] ?? top.reason?.en}</p>
            </div>
          ) : null}
        </div>
      </DismissibleHero>

      <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
        <div className="grid gap-4">
          <header>
            <p className="page-kicker">{t.kicker}</p>
            <h1 className="section-title">{t.title}</h1>
            <p className="mt-1 text-sm text-muted">{t.subtitle}</p>
          </header>
          <FeedFilters locale={params.locale} categories={taxonomy.categories} currentVertical={currentVertical} currentSort={currentSort} />
          {top ? <ContentCard item={top} locale={params.locale} featured /> : null}
          {rest.map((item) => (
            <ContentCard key={item.id} item={item} locale={params.locale} />
          ))}
          {!top ? <div className="tool-panel text-sm font-semibold text-muted">{t.empty}</div> : null}
          <LoadMore locale={params.locale} initialCursor={page.next_cursor} vertical={currentVertical} sort={currentSort} />
        </div>
        <Sidebar locale={params.locale} />
      </div>
    </section>
  );
}
