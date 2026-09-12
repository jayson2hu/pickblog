"use client";

import { TaxonomyCategory } from "../lib/taxonomy";

const labels = {
  en: { all: "All", recommended: "Recommended", latest: "Latest", top: "Top score" },
  zh: { all: "全部", recommended: "推荐", latest: "最新", top: "最高分" }
};

function queryHref(locale: string, next: { vertical?: string; sort?: string }, current: { vertical?: string; sort: string }) {
  const params = new URLSearchParams();
  const vertical = next.vertical === undefined ? current.vertical : next.vertical;
  const sort = next.sort ?? current.sort;
  if (vertical) params.set("vertical", vertical);
  if (sort && sort !== "recommended") params.set("sort", sort);
  const query = params.toString();
  return `/${locale}${query ? `?${query}` : ""}`;
}

function categoryLabel(category: TaxonomyCategory, locale: string) {
  if (locale === "zh") return category.label_zh ?? category.label;
  return category.label_en ?? category.label;
}

export function FeedFilters({
  locale,
  categories,
  currentVertical,
  currentSort
}: {
  locale: string;
  categories: TaxonomyCategory[];
  currentVertical?: string;
  currentSort: string;
}) {
  const t = labels[locale as "en" | "zh"] ?? labels.en;
  const sortedCategories = [...categories].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));

  return (
    <section className="filter-bar" aria-label={locale === "zh" ? "阅读筛选" : "Reading filters"}>
      <div className="chip-row">
        <a className={`chip${!currentVertical ? " chip-active" : ""}`} href={queryHref(locale, { vertical: "" }, { vertical: currentVertical, sort: currentSort })}>
          {t.all}
        </a>
        {sortedCategories.map((category) => (
          <a
            className={`chip${currentVertical === category.code ? " chip-active" : ""}`}
            key={category.code}
            href={queryHref(locale, { vertical: category.code }, { vertical: currentVertical, sort: currentSort })}
          >
            {categoryLabel(category, locale)}
          </a>
        ))}
      </div>
      <div className="segmented" role="group" aria-label={locale === "zh" ? "排序" : "Sort"}>
        <a className={currentSort === "recommended" ? "segment-active" : ""} href={queryHref(locale, { sort: "recommended" }, { vertical: currentVertical, sort: currentSort })}>
          {t.recommended}
        </a>
        <a className={currentSort === "published_at" ? "segment-active" : ""} href={queryHref(locale, { sort: "published_at" }, { vertical: currentVertical, sort: currentSort })}>
          {t.latest}
        </a>
        <a className={currentSort === "score" ? "segment-active" : ""} href={queryHref(locale, { sort: "score" }, { vertical: currentVertical, sort: currentSort })}>
          {t.top}
        </a>
      </div>
    </section>
  );
}
