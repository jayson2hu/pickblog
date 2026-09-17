import type { ContentSummary } from "../lib/api";
import { provenanceLabels } from "../lib/presentation";

export function ProvenanceStrip({ item, locale, compact = false }: { item: ContentSummary; locale: string; compact?: boolean }) {
  return (
    <div className={compact ? "provenance-strip provenance-compact" : "provenance-strip"} aria-label={locale === "zh" ? "内容处理说明" : "Content provenance"}>
      {provenanceLabels(item, locale).map((label, index) => (
        <span className="provenance-item" key={label}><span className={index === 0 ? "status-dot status-source" : index === 1 ? "status-dot status-analysis" : "status-dot"} aria-hidden="true" />{label}</span>
      ))}
    </div>
  );
}
