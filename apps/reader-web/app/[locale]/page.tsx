import { ContentCard } from "../../components/ContentCard";
import { FeedFilters } from "../../components/FeedFilters";
import { LoadMore } from "../../components/LoadMore";
import { Sidebar } from "../../components/Sidebar";
import { getFeedPage, normalizeSort } from "../../lib/api";
import { fallbackTaxonomyFromFeed, getTaxonomy } from "../../lib/taxonomy";

const copy = {
  en: {
    title: "Public picks", kicker: "Today’s engineering reading",
    subtitle: "A small queue of public-source engineering articles, with the source and automated processing method visible before you commit.",
    search: "Search titles and summaries", searchButton: "Search", queue: "Reading queue",
    queueNote: "Open the source for the publisher’s full text. CodePick summaries and scores are processing aids, not editorial endorsements.",
    empty: "No public picks match this view.", emptyHelp: "Try a broader search or reset the filters. If the queue remains empty, the source pipeline may not have completed new items yet.",
    reset: "Reset view", source: "Public source", analysis: "Automated analysis", review: "Review status shown"
  },
  zh: {
    title: "公共精选", kicker: "今天的工程阅读",
    subtitle: "少而明确的公开来源技术文章队列；在打开之前即可看到来源、自动处理方式和复核状态。",
    search: "搜索标题和摘要", searchButton: "搜索", queue: "阅读队列",
    queueNote: "发布者原文以来源链接为准。CodePick 摘要与评分用于辅助筛选，不代表编辑背书。",
    empty: "当前视图没有匹配的公开精选。", emptyHelp: "可以放宽搜索或重置筛选。如果仍为空，可能是来源管道尚未完成新内容。",
    reset: "重置视图", source: "公开来源", analysis: "自动分析", review: "显示复核状态"
  }
};

export default async function Home({ params, searchParams }: {
  params: Promise<{ locale: string }>; searchParams?: Promise<{ vertical?: string; sort?: string; q?: string }>;
}) {
  const { locale } = await params;
  const query = searchParams ? await searchParams : {};
  const t = copy[locale as "en" | "zh"] ?? copy.en;
  const currentSort = normalizeSort(query.sort);
  const currentVertical = query.vertical;
  const currentQuery = query.q?.trim() ?? "";
  const page = await getFeedPage({ vertical: currentVertical, sort: currentSort, q: currentQuery });
  const items = page.items;
  const taxonomy = (await getTaxonomy(locale)) ?? fallbackTaxonomyFromFeed(items, locale);
  const top = items[0];
  const rest = items.slice(1);

  return (
    <section className="reading-home">
      <header className="editorial-header">
        <div><p className="page-kicker">{t.kicker}</p><h1 className="page-title">{t.title}</h1><p className="page-subtitle">{t.subtitle}</p></div>
        <div className="trust-legend" aria-label={locale === "zh" ? "内容可信说明" : "Content trust guide"}>
          <span><i className="status-dot status-source" aria-hidden="true" />{t.source}</span>
          <span><i className="status-dot status-analysis" aria-hidden="true" />{t.analysis}</span>
          <span><i className="status-dot" aria-hidden="true" />{t.review}</span>
        </div>
      </header>
      <form className="search-bar" action={`/${locale}`} role="search">
        <label className="sr-only" htmlFor="feed-search">{t.search}</label>
        <input id="feed-search" name="q" type="search" defaultValue={currentQuery} placeholder={t.search} />
        {currentVertical ? <input name="vertical" type="hidden" value={currentVertical} /> : null}
        {currentSort !== "recommended" ? <input name="sort" type="hidden" value={currentSort} /> : null}
        <button className="primary-button" type="submit">{t.searchButton}</button>
      </form>
      <div className="reader-layout">
        <div className="grid min-w-0 gap-4">
          <div className="queue-heading"><div><h2 className="section-title">{t.queue}</h2><p className="mt-1 text-sm leading-6 text-muted">{t.queueNote}</p></div>{typeof page.total === "number" ? <span className="tag">{page.total}</span> : null}</div>
          <FeedFilters locale={locale} categories={taxonomy.categories} currentVertical={currentVertical} currentSort={currentSort} currentQuery={currentQuery} />
          {top ? <ContentCard item={top} locale={locale} featured /> : null}
          {rest.map((item) => <ContentCard key={item.id} item={item} locale={locale} />)}
          {!top ? <section className="state-panel text-center"><h2 className="section-title">{t.empty}</h2><p className="mt-3 text-sm leading-6 text-muted">{t.emptyHelp}</p><a className="secondary-button mt-5" href={`/${locale}`}>{t.reset}</a></section> : null}
          <LoadMore locale={locale} initialCursor={page.next_cursor} vertical={currentVertical} sort={currentSort} query={currentQuery} />
        </div>
        <Sidebar locale={locale} />
      </div>
    </section>
  );
}
