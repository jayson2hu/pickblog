import { BriefGate } from "../../../components/BriefGate";
import { TrackedContentLink } from "../../../components/TrackedContentLink";
import { getFeed } from "../../../lib/api";

export default async function BriefPage({ params }: { params: { locale: string } }) {
  const items = await getFeed();
  return (
    <section className="grid gap-8">
      <header className="grid gap-6 lg:grid-cols-[1fr_360px] lg:items-end">
        <div>
          <p className="page-kicker">{params.locale === "zh" ? "\u65e9\u62a5" : "Brief"}</p>
          <h1 className="page-title">{params.locale === "zh" ? "\u4eca\u65e5\u65e9\u62a5" : "Daily brief"}</h1>
          <p className="page-subtitle">
            {params.locale === "zh" ? "\u57fa\u4e8e COMPLETED \u5185\u5bb9\u7684\u516c\u5171\u65e9\u62a5\uff0cPro \u7528\u6237\u53ef\u540c\u6b65\u4e2a\u4eba\u65e9\u62a5\u3002" : "A completed-only public brief with Pro personal brief sync."}
          </p>
        </div>
        <div className="tool-panel">
          <p className="metric-label">{params.locale === "zh" ? "\u961f\u5217\u72b6\u6001" : "Queue status"}</p>
          <p className="metric-value">{items.length} ready</p>
          <p className="mt-2 text-sm text-muted">Arq / Email / Public API</p>
        </div>
      </header>
      <BriefGate locale={params.locale} />
      <div className="grid gap-3">
        {items.map((item, index) => (
          <TrackedContentLink key={item.id} contentId={item.id} href={`/${params.locale}/items/${item.id}`} className="content-card grid gap-3 p-4 md:grid-cols-[76px_1fr_120px] md:items-center">
            <span className="text-sm font-bold text-accent">#{index + 1}</span>
            <span>
              <span className="block text-lg font-bold">{item.title}</span>
              <span className="mt-1 block text-sm leading-6 text-muted">{item.summary}</span>
            </span>
            <span className="tag justify-center">{item.scores.quality}</span>
          </TrackedContentLink>
        ))}
      </div>
    </section>
  );
}
