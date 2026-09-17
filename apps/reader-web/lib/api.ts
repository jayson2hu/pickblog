export type ContentProvenance = {
  source_kind?: "public_feed" | "fixture" | "unknown";
  analysis_method?: string;
  scoring_method?: "heuristic" | "simulated" | "model";
  model?: string;
  translation_available?: boolean;
  source_url?: string;
  reviewed?: boolean;
};

export type ContentSummary = {
  id: string;
  title: string;
  source: string;
  url: string;
  vertical: string;
  published_at: string | null;
  thumbnail?: string;
  summary: string;
  scores: Record<string, number>;
  read_time_minutes?: number;
  reason?: { en: string; zh: string };
  language?: string;
  reading_minutes?: number;
  tags?: string[];
  provenance?: ContentProvenance;
};

export type ContentDetail = ContentSummary & {
  base_analysis: { summary: string; viewpoints: string[]; quotes: string[] };
  translations: Record<string, { title: string; summary: string; base_analysis: ContentDetail["base_analysis"] }>;
  paragraphs?: { en: string; zh: string }[];
};

export type FeedOptions = { q?: string; vertical?: string; sort?: string; cursor?: string; limit?: number };
export type FeedPage = { items: ContentSummary[]; next_cursor?: string | null; total?: number };

const fallbackItems: ContentDetail[] = [{
  id: "cp-001",
  title: "Async Python agents are getting cheaper to operate",
  source: "CodePick Research",
  url: "https://example.com/async-python-agents",
  vertical: "ai",
  published_at: "2026-05-29T08:00:00Z",
  summary: "A practical look at queue-backed agent systems and cost controls.",
  scores: { quality: 92, novelty: 84, relevance: 91, depth: 88, clarity: 86, impact: 89 },
  read_time_minutes: 6,
  language: "en",
  reading_minutes: 6,
  tags: ["AI", "Python", "agents"],
  provenance: {
    source_kind: "fixture", analysis_method: "extractive-v1", scoring_method: "simulated",
    translation_available: true, source_url: "https://example.com/async-python-agents", reviewed: false
  },
  reason: { en: "Fixture item ranked with simulated signals for interface testing.", zh: "界面测试样例，使用模拟信号排序。" },
  base_analysis: {
    summary: "Queue-backed agents can keep latency predictable while reducing idle model time.",
    viewpoints: ["Batch non-urgent work", "Measure tool failure rates", "Separate orchestration from scoring"],
    quotes: ["Cheaper agents start with better queues."]
  },
  translations: {
    zh: {
      title: "异步 Python 智能体的运行成本正在下降",
      summary: "一篇关于队列驱动智能体系统与成本控制的实践分析。",
      base_analysis: {
        summary: "队列驱动的智能体可以降低模型空转时间，并让延迟更可预测。",
        viewpoints: ["批处理非紧急任务", "衡量工具失败率", "拆分编排与评分"],
        quotes: ["更低成本的智能体始于更好的队列。"]
      }
    }
  },
  paragraphs: [
    { en: "Queue-backed agent systems move slow or failure-prone work out of the request path, keeping the reader experience predictable.", zh: "队列驱动的智能体系统把慢任务和易失败任务移出请求链路，让阅读体验更可预测。" },
    { en: "The strongest teams measure queue delay, tool failure, and idle model time before adding more orchestration.", zh: "成熟团队会先衡量排队延迟、工具失败和模型空转时间，再增加编排复杂度。" }
  ]
}];

export const apiBase = process.env.READER_API_BASE ?? process.env.NEXT_PUBLIC_READER_API_BASE ?? "http://127.0.0.1:8000";
const demoFallbackEnabled = process.env.READER_USE_DEMO_FALLBACK === "true";
const contentFetchOptions = demoFallbackEnabled ? { next: { revalidate: 60 } } : { cache: "no-store" as const };
const validSorts = new Set(["recommended", "published_at", "score"]);

export function normalizeSort(sort?: string) {
  if (!sort || !validSorts.has(sort)) return "recommended";
  return sort;
}

function feedUrl(options: FeedOptions = {}) {
  const url = new URL(`${apiBase}/api/feed`);
  if (options.q) url.searchParams.set("q", options.q);
  if (options.vertical) url.searchParams.set("vertical", options.vertical);
  if (options.cursor) url.searchParams.set("cursor", options.cursor);
  if (options.limit) url.searchParams.set("limit", String(options.limit));
  const sort = normalizeSort(options.sort);
  url.searchParams.set("sort", sort === "recommended" ? "score" : sort);
  return url.toString();
}

export async function getFeedPage(options: FeedOptions = {}): Promise<FeedPage> {
  try {
    const response = await fetch(feedUrl(options), contentFetchOptions);
    if (!response.ok) throw new Error("feed request failed");
    const page = await response.json();
    return { items: (page.items ?? []).map(enrichSummary), next_cursor: page.next_cursor ?? null, total: page.total };
  } catch (error) {
    if (!demoFallbackEnabled) throw error;
    const needle = options.q?.trim().toLocaleLowerCase();
    const filtered = fallbackItems.filter((item) => {
      const matchesVertical = !options.vertical || item.vertical === options.vertical;
      const matchesQuery = !needle || `${item.title} ${item.summary} ${item.source}`.toLocaleLowerCase().includes(needle);
      return matchesVertical && matchesQuery;
    });
    const sorted = [...filtered].sort((a, b) => {
      if (normalizeSort(options.sort) === "published_at") return new Date(b.published_at ?? 0).getTime() - new Date(a.published_at ?? 0).getTime();
      return (b.scores.quality ?? 0) - (a.scores.quality ?? 0);
    });
    return { items: sorted.map(enrichSummary), next_cursor: null, total: sorted.length };
  }
}

export async function getFeed(options: FeedOptions = {}) {
  return (await getFeedPage(options)).items;
}

export async function getItem(id: string): Promise<ContentDetail | undefined> {
  try {
    const response = await fetch(`${apiBase}/api/read/${id}`, contentFetchOptions);
    if (response.status === 404) return undefined;
    if (!response.ok) throw new Error(`item request failed: ${response.status}`);
    return enrichDetail(await response.json());
  } catch (error) {
    if (!demoFallbackEnabled) throw error;
    return fallbackItems.find((item) => item.id === id);
  }
}

function estimateReadMinutes(item: Pick<ContentSummary, "summary" | "title">) {
  const words = `${item.title} ${item.summary}`.trim().split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.round(words / 200));
}

function reasonFor(item: ContentSummary): { en: string; zh: string } {
  if (item.provenance?.source_kind === "fixture" || item.provenance?.scoring_method === "simulated") {
    return { en: "Fixture item ranked with simulated signals for interface testing.", zh: "界面测试样例，使用模拟信号排序。" };
  }
  const scores = item.scores ?? {};
  if ((scores.depth ?? 0) >= 88 && (scores.impact ?? 0) >= 88) return { en: "Rule-based depth and impact signals placed this in the reading queue.", zh: "规则分析中的深度与影响信号使其进入阅读队列。" };
  if ((scores.novelty ?? 0) >= (scores.quality ?? 0)) return { en: "Rule-based novelty signals placed this in the reading queue.", zh: "规则分析中的新颖度信号使其进入阅读队列。" };
  return { en: "Automated signals placed this in the current reading queue.", zh: "自动分析信号使其进入当前阅读队列。" };
}

function enrichSummary<T extends ContentSummary>(item: T): T {
  return {
    ...item,
    reading_minutes: item.reading_minutes ?? item.read_time_minutes ?? estimateReadMinutes(item),
    read_time_minutes: item.read_time_minutes ?? item.reading_minutes ?? estimateReadMinutes(item),
    reason: item.reason ?? reasonFor(item)
  };
}

function enrichDetail(item: ContentDetail): ContentDetail {
  return enrichSummary(item);
}
