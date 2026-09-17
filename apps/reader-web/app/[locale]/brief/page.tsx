import { BriefGate } from "../../../components/BriefGate";
import { ProvenanceStrip } from "../../../components/ProvenanceStrip";
import { TrackedContentLink } from "../../../components/TrackedContentLink";
import { getFeed } from "../../../lib/api";
import { formatPublishedDate, sourceHost } from "../../../lib/presentation";

export default async function BriefPage({ params }: { params: Promise<{ locale: string }> }) {
  const [{ locale }, items] = await Promise.all([params, getFeed()]);
  const isZh = locale === "zh";
  return <section className="grid gap-8">
    <header className="editorial-header">
      <div><p className="page-kicker">{isZh ? "公共阅读清单" : "Public reading list"}</p><h1 className="page-title">{isZh ? "今日早报" : "Daily brief"}</h1><p className="page-subtitle">{isZh ? "按当前排序规则生成的公开清单。它不是人工编辑早报；来源和自动处理方式会逐条展示。" : "A public list produced by the current ordering rules. It is not a human-edited newsletter; source and processing details remain visible per item."}</p></div>
      <div className="trust-note"><p className="metric-label">{isZh ? "当前边界" : "Current boundary"}</p><p>{isZh ? "邮件发送与真实个性化不在本机验收范围内。" : "Email delivery and production personalization are outside this local acceptance environment."}</p></div>
    </header>
    <BriefGate locale={locale} />
    {items.length ? <div className="brief-list">{items.map((item, index) => <article className="brief-item" key={item.id}>
      <span className="brief-index">{String(index + 1).padStart(2, "0")}</span>
      <div className="min-w-0"><div className="source-line"><span>{sourceHost(item)}</span><span>·</span><span>{formatPublishedDate(item.published_at, locale)}</span></div><h2 className="mt-2 text-xl font-bold"><TrackedContentLink contentId={item.id} href={`/${locale}/items/${item.id}`}>{item.title}</TrackedContentLink></h2><p className="mt-2 text-sm leading-6 text-muted">{item.summary}</p><ProvenanceStrip item={item} locale={locale} compact /></div>
    </article>)}</div> : <section className="state-panel text-center">{isZh ? "当前没有已完成的公开内容。" : "No completed public content is available."}</section>}
  </section>;
}
