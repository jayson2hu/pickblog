const palette: Record<string, [string, string]> = {
  ai: ["#4f46e5", "#14b8a6"],
  data: ["#0f766e", "#2563eb"],
  infra: ["#334155", "#4f46e5"],
  product: ["#7c3aed", "#db2777"]
};

export function CoverThumb({ source, vertical, thumbnail }: { source: string; vertical: string; thumbnail?: string }) {
  if (thumbnail) {
    return <img className="cover-thumb" src={thumbnail} alt="" />;
  }
  const [from, to] = palette[vertical] ?? ["#4f46e5", "#64748b"];
  const initials = source
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase();
  return (
    <div className="cover-thumb cover-fallback" style={{ background: `linear-gradient(135deg, ${from}, ${to})` }}>
      <span>{initials}</span>
      <small>{vertical}</small>
    </div>
  );
}
