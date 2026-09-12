import { apiBase, ContentSummary } from "./api";

export type TaxonomyCategory = {
  code: string;
  label: string;
  label_en?: string;
  label_zh?: string;
  color_from?: string;
  color_to?: string;
  sort_order?: number;
  active?: boolean;
};

export type Taxonomy = {
  categories: TaxonomyCategory[];
  audience?: { code: string; label: string; categories?: string[] };
  audiences?: { code: string; label: string }[];
};

export async function getTaxonomy(locale: string, token?: string): Promise<Taxonomy | null> {
  try {
    const response = await fetch(`${apiBase}/api/taxonomy`, {
      headers: {
        "Accept-Language": locale,
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      next: { revalidate: 60 }
    });
    if (!response.ok) throw new Error("taxonomy request failed");
    const body = await response.json();
    return {
      categories: (body.categories ?? []).filter((category: TaxonomyCategory) => category.active !== false),
      audience: body.audience,
      audiences: body.audiences ?? []
    };
  } catch {
    return null;
  }
}

export function fallbackTaxonomyFromFeed(items: ContentSummary[], locale: string): Taxonomy {
  const seen = new Set<string>();
  const categories = items
    .map((item) => item.vertical)
    .filter((vertical) => {
      if (seen.has(vertical)) return false;
      seen.add(vertical);
      return true;
    })
    .map((vertical, index) => ({
      code: vertical,
      label: vertical,
      label_en: vertical,
      label_zh: vertical,
      sort_order: index,
      active: true
    }));
  return {
    categories,
    audience: { code: "fallback", label: locale === "zh" ? "本地分类" : "Local categories", categories: categories.map((category) => category.code) },
    audiences: []
  };
}
