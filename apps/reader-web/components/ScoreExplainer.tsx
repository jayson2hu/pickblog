const scoreCopy: Record<string, { en: string; zh: string }> = {
  quality: { en: "Overall automated confidence.", zh: "自动分析的综合置信信号。" },
  novelty: { en: "New signal compared with the current corpus.", zh: "相对当前语料的新增信号。" },
  relevance: { en: "Rule-based audience fit.", zh: "规则计算的受众匹配度。" },
  depth: { en: "Evidence of substance beyond a short update.", zh: "是否包含超过简讯的信息深度。" },
  clarity: { en: "Detected structure and readability.", zh: "检测到的结构与可读性。" },
  impact: { en: "Potential relevance to engineering decisions.", zh: "对工程决策的潜在关联。" }
};

export function ScoreExplainer({ scores, locale, method }: { scores: Record<string, number>; locale: string; method?: string }) {
  const isZh = locale === "zh";
  const methodLabel = method === "heuristic" ? (isZh ? "规则评分" : "Heuristic scoring") : method === "simulated" ? (isZh ? "模拟评分，仅供测试" : "Simulated scoring for tests") : method === "model" ? (isZh ? "模型评分" : "Model scoring") : (isZh ? "评分方法未知" : "Scoring method unknown");

  if (method === "heuristic") {
    return <section className="reading-section">
      <div className="section-heading-row"><div><p className="section-eyebrow">{isZh ? "处理明细" : "Processing detail"}</p><h2 className="section-title">{isZh ? "规则排序" : "Rule-based ordering"}</h2></div><span className="tag">{methodLabel}</span></div>
      <p className="mt-3 text-sm leading-6 text-muted">{isZh ? "系统使用可重复的规则信号安排阅读顺序；未评估维度的中性占位值不作为质量结论展示。" : "Repeatable rule signals set the reading order. Neutral placeholder values for unevaluated dimensions are not shown as quality judgments."}</p>
    </section>;
  }

  return <section className="reading-section">
    <div className="section-heading-row"><div><p className="section-eyebrow">{isZh ? "处理明细" : "Processing detail"}</p><h2 className="section-title">{isZh ? "六维评分" : "Six-dimension scores"}</h2></div><span className="tag">{methodLabel}</span></div>
    <p className="mt-3 text-sm leading-6 text-muted">{isZh ? "这些数值来自自动处理，用于排序与调试，不代表专家评审或客观质量。" : "These values come from automated processing for ranking and inspection. They are not expert review or objective quality."}</p>
    <dl className="mt-4 score-grid">{Object.entries(scores).map(([key, value]) => <div key={key} className="metric-cell"><dt className="metric-label capitalize">{key}</dt><dd className="metric-value">{value}</dd><p className="mt-2 text-sm text-muted">{scoreCopy[key]?.[locale as "en" | "zh"] ?? key}</p></div>)}</dl>
  </section>;
}
