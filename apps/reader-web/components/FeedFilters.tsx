"use client";

import { TaxonomyCategory } from "../lib/taxonomy";

const labels = {
  en: { all: "All topics", recommended: "For this queue", latest: "Newest", top: "Score detail" },
  zh: { all: "全部主题", recommended: "当前队列", latest: "最新发布", top: "评分排序" }
};

function queryHref(locale: string, next: { vertical?: string; sort?: string }, current: { vertical?: string; sort: string; q?: string }) {
  const params = new URLSearchParams();
  const vertical = next.vertical === undefined ? current.vertical : next.vertical;
  const sort = next.sort ?? current.sort;
  if (current.q) params.set("q", current.q);
  if (vertical) params.set("vertical", vertical);
  if (sort && sort !== "recommended") params.set("sort", sort);
  const query = params.toString();
  return `/${locale}${query ? `?${query}` : ""}`;
}

function categoryLabel(category: TaxonomyCategory, locale: string) {
  return locale === "zh" ? category.label_zh ?? category.label : category.label_en ?? category.label;
}

export function FeedFilters({ locale, categories, currentVertical, currentSort, currentQuery }: {
  locale: string; categories: TaxonomyCategory[]; currentVertical?: string; currentSort: string; currentQuery?: string;
}) {
  const t = labels[locale as "en" | "zh"] ?? labels.en;
  const sortedCategories = [...categories].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
  const current = { vertical: currentVertical, sort: currentSort, q: currentQuery };
  return (
    <section className="filter-bar" aria-label={locale === "zh" ? "阅读筛选" : "Reading filters"}>
      <div className="chip-row">
        <a className={`chip${!currentVertical ? " chip-active" : ""}`} href={queryHref(locale, { vertical: "" }, current)}>{t.all}</a>
        {sortedCategories.map((category) => <a className={`chip${currentVertical === category.code ? " chip-active" : ""}`} key={category.code} href={queryHref(locale, { vertical: category.code }, current)}>{categoryLabel(category, locale)}</a>)}
      </div>
      <div className="segmented" role="group" aria-label={locale === "zh" ? "排序" : "Sort"}>
        <a className={currentSort === "recommended" ? "segment-active" : ""} href={queryHref(locale, { sort: "recommended" }, current)}>{t.recommended}</a>
        <a className={currentSort === "published_at" ? "segment-active" : ""} href={queryHref(locale, { sort: "published_at" }, current)}>{t.latest}</a>
        <a className={currentSort === "score" ? "segment-active" : ""} href={queryHref(locale, { sort: "score" }, current)}>{t.top}</a>
      </div>
    </section>
  );
}
