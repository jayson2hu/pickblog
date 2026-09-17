import { ApiKeyPanel } from "../../../components/ApiKeyPanel";
import { ApiUsageChart } from "../../../components/ApiUsageChart";

export default async function DevelopersPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const isZh = locale === "zh";
  return <section className="grid gap-8">
    <header className="editorial-header"><div><p className="page-kicker">{isZh ? "本地开发接口" : "Local developer interface"}</p><h1 className="page-title">{isZh ? "开发者" : "Developers"}</h1><p className="page-subtitle">{isZh ? "验证公开内容 API、字段边界和密钥生命周期。MCP 传输与生产配额尚未在本机完成验收。" : "Validate the public content API, field boundary, and key lifecycle. MCP transport and production quotas are not accepted in this local environment."}</p></div><span className="environment-badge">{isZh ? "开发环境" : "Development"}</span></header>
    <div className="grid gap-6 lg:grid-cols-[1fr_0.9fr]">
      <div className="grid gap-6">
        <section className="tool-panel"><p className="section-eyebrow">{isZh ? "本机请求" : "Local request"}</p><h2 className="section-title mt-1">{isZh ? "快速开始" : "Quick start"}</h2><pre className="code-block">{`curl -H "X-API-Key: cp_test_key" \\\n  http://127.0.0.1:8001/v1/today`}</pre></section>
        <section className="tool-panel"><h2 className="section-title">{isZh ? "公开字段边界" : "Public field boundary"}</h2><div className="mt-4 grid gap-3 text-sm leading-6 text-muted"><p>{isZh ? "接口只返回公开契约允许的内容字段。" : "The API returns only fields allowed by the public contract."}</p><p>{isZh ? "私有用户上下文和未完成内容不会通过此接口分发。" : "Private user context and incomplete content do not leave this boundary."}</p><p>{isZh ? "MCP 的 today / search / item 仍属于待验收传输能力。" : "MCP today / search / item remain transport capabilities to validate."}</p></div></section>
        <ApiUsageChart locale={locale} />
      </div>
      <ApiKeyPanel locale={locale} />
    </div>
  </section>;
}
