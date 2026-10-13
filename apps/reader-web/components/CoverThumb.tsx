const topics: Record<string, string> = { ai: "INTELLIGENCE", data: "DATA SYSTEMS", infra: "INFRASTRUCTURE", product: "PRODUCT THINKING" };

/** Original topic artwork; decorative, never presented as a source image. */
export function CoverThumb({ source, vertical, thumbnail }: { source: string; vertical: string; thumbnail?: string }) {
  if (thumbnail) return <img className="cover-thumb" src={thumbnail} alt="" loading="lazy" />;
  return (
    <div className={`cover-thumb cover-fallback artwork-${vertical}`} aria-hidden="true">
      <div className="artwork-caption"><span>CODEPICK / NOTES</span><span>↗</span></div>
      <svg className="topic-art" viewBox="0 0 240 180" fill="none">
        <circle cx="120" cy="90" r="70" stroke="currentColor" strokeWidth="1" />
        <ellipse cx="120" cy="90" rx="40" ry="70" stroke="currentColor" />
        <ellipse cx="120" cy="90" rx="16" ry="70" stroke="currentColor" />
        <ellipse cx="120" cy="90" rx="70" ry="26" stroke="currentColor" />
        <path d="M50 90h140M62 50h116M62 130h116" stroke="currentColor" />
        <circle cx="171" cy="42" r="9" fill="currentColor" />
      </svg>
      <div className="artwork-footer"><strong>{topics[vertical] ?? vertical.toUpperCase()}</strong><small>{source}</small></div>
    </div>
  );
}
