import { BillingPanel } from "../../../components/BillingPanel";

export default function PricingPage({ params }: { params: { locale: string } }) {
  const isZh = params.locale === "zh";
  return (
    <section className="grid gap-8">
      <header>
        <p className="page-kicker">{isZh ? "\u8ba2\u9605" : "Subscription"}</p>
        <h1 className="page-title">{isZh ? "Free \u4e0e Pro" : "Free and Pro"}</h1>
        <p className="page-subtitle">{isZh ? "\u5728\u4f34\u8bfb\u914d\u989d\u7528\u5c3d\u3001\u4e2a\u6027\u5316\u65e9\u62a5\u548c\u6df1\u5ea6\u5de5\u4f5c\u6d41\u5904\u5347\u7ea7\u3002" : "Upgrade where the workflow creates value: companion quota, personal briefs, and focused reading."}</p>
      </header>
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="tool-panel">
          <h2 className="section-title">Free</h2>
          <ul className="mt-4 grid gap-3 text-sm text-muted">
            <li>{isZh ? "\u516c\u5171\u7cbe\u9009\u4fe1\u606f\u6d41" : "Public picks feed"}</li>
            <li>{isZh ? "\u6709\u9650 AI \u4f34\u8bfb" : "Limited AI companion"}</li>
            <li>{isZh ? "\u516c\u5171\u65e9\u62a5" : "Public daily brief"}</li>
          </ul>
        </section>
        <section className="tool-panel">
          <h2 className="section-title">Pro</h2>
          <ul className="mt-4 grid gap-3 text-sm text-muted">
            <li>{isZh ? "\u65e0\u9650 AI \u4f34\u8bfb" : "Unlimited AI companion"}</li>
            <li>{isZh ? "\u4e2a\u6027\u5316\u65e9\u62a5" : "Personalized daily brief"}</li>
            <li>{isZh ? "\u66f4\u9ad8 API \u5206\u53d1\u914d\u989d" : "Higher distribution quota"}</li>
          </ul>
        </section>
      </div>
      <BillingPanel locale={params.locale} />
    </section>
  );
}
