import { ApiKeyPanel } from "../../../components/ApiKeyPanel";
import { ApiUsageChart } from "../../../components/ApiUsageChart";

export default function DevelopersPage({ params }: { params: { locale: string } }) {
  const isZh = params.locale === "zh";
  return (
    <section className="grid gap-8">
      <header>
        <p className="page-kicker">{isZh ? "\u5206\u53d1" : "Distribution"}</p>
        <h1 className="page-title">{isZh ? "\u5f00\u53d1\u8005" : "Developers"}</h1>
        <p className="page-subtitle">
          {isZh ? "\u7528 Public API \u548c MCP \u628a COMPLETED \u5185\u5bb9\u5b89\u5168\u5206\u53d1\u5230\u4f60\u7684\u5de5\u5177\u3002" : "Use the Public API and MCP wrappers to distribute completed content safely."}
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1fr_0.9fr]">
        <div className="grid gap-6">
          <section className="tool-panel">
            <h2 className="section-title">{isZh ? "\u5feb\u901f\u5f00\u59cb" : "Quick start"}</h2>
            <pre className="mt-4 overflow-x-auto rounded-md bg-panel p-4 text-sm">{`curl -H "X-API-Key: cp_test_key" \\
  http://127.0.0.1:8001/v1/today`}</pre>
          </section>
          <section className="tool-panel">
            <h2 className="section-title">{isZh ? "\u5b57\u6bb5\u8fb9\u754c" : "Field boundary"}</h2>
            <div className="mt-4 grid gap-3 text-sm text-muted">
              <p>{isZh ? "\u53ea\u8fd4\u56de public_contract.py \u5141\u8bb8\u7684\u516c\u5171\u5b57\u6bb5\u3002" : "Only fields allowed by public_contract.py are returned."}</p>
              <p>{isZh ? "\u4e0d\u51fa\u7ad9 base_analysis\u3001\u7528\u6237\u4e0a\u4e0b\u6587\u6216\u975e COMPLETED \u5185\u5bb9\u3002" : "No base_analysis, private user context, or non-COMPLETED content leaves the boundary."}</p>
              <p>MCP: today / search / item</p>
            </div>
          </section>
          <ApiUsageChart locale={params.locale} />
        </div>
        <ApiKeyPanel locale={params.locale} />
      </div>
    </section>
  );
}
