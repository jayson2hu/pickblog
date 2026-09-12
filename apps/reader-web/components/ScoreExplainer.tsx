const scoreCopy: Record<string, { en: string; zh: string }> = {
  quality: { en: "Overall editorial confidence.", zh: "整体编辑判断信心。" },
  novelty: { en: "How much new signal it adds.", zh: "新增信息量与新鲜度。" },
  relevance: { en: "Fit for the current audience.", zh: "与当前受众的匹配度。" },
  depth: { en: "Substance beyond surface summary.", zh: "是否超过表层摘要。" },
  clarity: { en: "Readable structure and evidence.", zh: "结构、论据与可读性。" },
  impact: { en: "Likely decision or practice impact.", zh: "对决策或实践的影响。" }
};

export function ScoreExplainer({ scores, locale }: { scores: Record<string, number>; locale: string }) {
  return (
    <section>
      <div className="flex items-end justify-between gap-4">
        <h2 className="section-title">{locale === "zh" ? "六维评分" : "Six-dimension scores"}</h2>
        <p className="text-sm text-muted">{locale === "zh" ? "评分来自 L2，L3 只读展示。" : "Scores come from L2 and remain read-only in L3."}</p>
      </div>
      <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {Object.entries(scores).map(([key, value]) => (
          <div key={key} className="metric-cell" title={scoreCopy[key]?.[locale as "en" | "zh"] ?? key}>
            <dt className="metric-label capitalize">{key}</dt>
            <dd className="metric-value">{value}</dd>
            <p className="mt-2 text-sm text-muted">{scoreCopy[key]?.[locale as "en" | "zh"] ?? key}</p>
          </div>
        ))}
      </dl>
    </section>
  );
}
