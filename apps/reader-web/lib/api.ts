export type ContentSummary = {
  id: string;
  title: string;
  source: string;
  url: string;
  vertical: string;
  published_at: string;
  thumbnail?: string;
  summary: string;
  scores: Record<string, number>;
  read_time_minutes?: number;
  reason?: { en: string; zh: string };
};

export type ContentDetail = ContentSummary & {
  base_analysis: { summary: string; viewpoints: string[]; quotes: string[] };
  translations: Record<string, { title: string; summary: string; base_analysis: ContentDetail["base_analysis"] }>;
  paragraphs?: { en: string; zh: string }[];
};

export type FeedOptions = {
  vertical?: string;
  sort?: string;
  cursor?: string;
  limit?: number;
};

export type FeedPage = {
  items: ContentSummary[];
  next_cursor?: string | null;
  total?: number;
};

const fallbackItems: ContentDetail[] = [
  {
    id: "cp-001",
    title: "Async Python agents are getting cheaper to operate",
    source: "CodePick Research",
    url: "https://example.com/async-python-agents",
    vertical: "ai",
    published_at: "2026-05-29T08:00:00Z",
    summary: "A practical look at queue-backed agent systems and cost controls.",
    scores: { quality: 92, novelty: 84, relevance: 91, depth: 88, clarity: 86, impact: 89 },
    read_time_minutes: 6,
    reason: {
      en: "High depth and impact make it useful for engineering decisions.",
      zh: "\u6df1\u5ea6\u4e0e\u5f71\u54cd\u53cc\u9ad8\uff0c\u9002\u5408\u505a\u5de5\u7a0b\u51b3\u7b56\u53c2\u8003\u3002"
    },
    base_analysis: {
      summary: "Queue-backed agents can keep latency predictable while reducing idle model time.",
      viewpoints: ["Batch non-urgent work", "Measure tool failure rates", "Separate orchestration from scoring"],
      quotes: ["Cheaper agents start with better queues."]
    },
    translations: {
      zh: {
        title: "\u5f02\u6b65 Python \u667a\u80fd\u4f53\u7684\u8fd0\u884c\u6210\u672c\u6b63\u5728\u4e0b\u964d",
        summary: "\u4e00\u7bc7\u5173\u4e8e\u961f\u5217\u9a71\u52a8\u667a\u80fd\u4f53\u7cfb\u7edf\u4e0e\u6210\u672c\u63a7\u5236\u7684\u5b9e\u8df5\u5206\u6790\u3002",
        base_analysis: {
          summary:
            "\u961f\u5217\u9a71\u52a8\u7684\u667a\u80fd\u4f53\u53ef\u4ee5\u964d\u4f4e\u6a21\u578b\u7a7a\u8f6c\u65f6\u95f4\uff0c\u5e76\u8ba9\u5ef6\u8fdf\u66f4\u53ef\u9884\u6d4b\u3002",
          viewpoints: [
            "\u6279\u5904\u7406\u975e\u7d27\u6025\u4efb\u52a1",
            "\u8861\u91cf\u5de5\u5177\u5931\u8d25\u7387",
            "\u62c6\u5206\u7f16\u6392\u4e0e\u8bc4\u5206"
          ],
          quotes: ["\u66f4\u4f4e\u6210\u672c\u7684\u667a\u80fd\u4f53\u59cb\u4e8e\u66f4\u597d\u7684\u961f\u5217\u3002"]
        }
      }
    },
    paragraphs: [
      {
        en: "Queue-backed agent systems move slow or failure-prone work out of the request path, keeping the reader experience predictable.",
        zh: "\u961f\u5217\u9a71\u52a8\u7684\u667a\u80fd\u4f53\u7cfb\u7edf\u628a\u6162\u4efb\u52a1\u548c\u6613\u5931\u8d25\u4efb\u52a1\u79fb\u51fa\u8bf7\u6c42\u94fe\u8def\uff0c\u8ba9\u9605\u8bfb\u4f53\u9a8c\u66f4\u53ef\u9884\u6d4b\u3002"
      },
      {
        en: "The strongest teams measure queue delay, tool failure, and idle model time before adding more orchestration.",
        zh: "\u6210\u719f\u56e2\u961f\u4f1a\u5148\u8861\u91cf\u6392\u961f\u5ef6\u8fdf\u3001\u5de5\u5177\u5931\u8d25\u548c\u6a21\u578b\u7a7a\u8f6c\u65f6\u95f4\uff0c\u518d\u589e\u52a0\u7f16\u6392\u590d\u6742\u5ea6\u3002"
      }
    ]
  }
];

export const apiBase = process.env.READER_API_BASE ?? process.env.NEXT_PUBLIC_READER_API_BASE ?? "http://127.0.0.1:8000";

const validSorts = new Set(["recommended", "published_at", "score"]);

export function normalizeSort(sort?: string) {
  if (!sort || !validSorts.has(sort)) return "recommended";
  return sort;
}

function feedUrl(options: FeedOptions = {}) {
  const url = new URL(`${apiBase}/api/feed`);
  if (options.vertical) url.searchParams.set("vertical", options.vertical);
  if (options.cursor) url.searchParams.set("cursor", options.cursor);
  if (options.limit) url.searchParams.set("limit", String(options.limit));
  const sort = normalizeSort(options.sort);
  url.searchParams.set("sort", sort === "recommended" ? "score" : sort);
  return url.toString();
}

export async function getFeedPage(options: FeedOptions = {}): Promise<FeedPage> {
  try {
    const response = await fetch(feedUrl(options), { next: { revalidate: 60 } });
    if (!response.ok) throw new Error("feed request failed");
    const page = await response.json();
    return {
      items: (page.items ?? []).map(enrichSummary),
      next_cursor: page.next_cursor ?? null,
      total: page.total
    };
  } catch {
    const filtered = options.vertical ? fallbackItems.filter((item) => item.vertical === options.vertical) : fallbackItems;
    const sorted = [...filtered].sort((a, b) => {
      if (normalizeSort(options.sort) === "published_at") {
        return new Date(b.published_at).getTime() - new Date(a.published_at).getTime();
      }
      return (b.scores.quality ?? 0) - (a.scores.quality ?? 0);
    });
    return { items: sorted.map(enrichSummary), next_cursor: null, total: sorted.length };
  }
}

export async function getFeed(options: FeedOptions = {}): Promise<ContentSummary[]> {
  const page = await getFeedPage(options);
  return page.items;
}

export async function getItem(id: string): Promise<ContentDetail | undefined> {
  try {
    const response = await fetch(`${apiBase}/api/read/${id}`, { next: { revalidate: 60 } });
    if (!response.ok) throw new Error("item request failed");
    return enrichDetail(await response.json());
  } catch {
    return fallbackItems.find((item) => item.id === id);
  }
}

function estimateReadMinutes(item: Pick<ContentSummary, "summary" | "title">) {
  const words = `${item.title} ${item.summary}`.trim().split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.round(words / 200));
}

function reasonFor(item: ContentSummary): { en: string; zh: string } {
  const scores = item.scores ?? {};
  if ((scores.depth ?? 0) >= 88 && (scores.impact ?? 0) >= 88) {
    return { en: "High depth and impact make it useful for engineering decisions.", zh: "\u6df1\u5ea6\u4e0e\u5f71\u54cd\u53cc\u9ad8\uff0c\u9002\u5408\u505a\u5de5\u7a0b\u51b3\u7b56\u53c2\u8003\u3002" };
  }
  if ((scores.novelty ?? 0) >= (scores.quality ?? 0)) {
    return { en: "High novelty makes it useful for scanning emerging trends.", zh: "\u65b0\u9c9c\u5ea6\u9ad8\uff0c\u9002\u5408\u5feb\u901f\u4e86\u89e3\u8d8b\u52bf\u3002" };
  }
  return { en: "Strong quality score makes it worth saving for focused reading.", zh: "\u8d28\u91cf\u5206\u7a33\u5b9a\uff0c\u503c\u5f97\u6536\u5165\u7a0d\u540e\u6df1\u8bfb\u3002" };
}

function enrichSummary<T extends ContentSummary>(item: T): T {
  return {
    ...item,
    read_time_minutes: item.read_time_minutes ?? estimateReadMinutes(item),
    reason: item.reason ?? reasonFor(item)
  };
}

function enrichDetail(item: ContentDetail): ContentDetail {
  return enrichSummary(item);
}
