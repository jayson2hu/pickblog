import { BillingPanel } from "../../../components/BillingPanel";

export default async function PricingPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const isZh = locale === "zh";
  return <section className="grid gap-8">
    <header className="editorial-header"><div><p className="page-kicker">{isZh ? "商业假设测试" : "Commercial hypothesis test"}</p><h1 className="page-title">{isZh ? "方案原型" : "Plan prototype"}</h1><p className="page-subtitle">{isZh ? "用于验证方案信息架构和沙箱结账流程，不是正式报价或可购买服务。" : "Used to validate plan information and the sandbox checkout flow. This is not a production offer or purchasable service."}</p></div><span className="environment-badge">{isZh ? "沙箱" : "Sandbox"}</span></header>
    <div className="grid gap-6 lg:grid-cols-2">
      <section className="tool-panel"><p className="section-eyebrow">{isZh ? "当前可用" : "Available now"}</p><h2 className="section-title mt-1">Free</h2><ul className="feature-list"><li>{isZh ? "浏览公开精选与来源链接" : "Browse public picks and source links"}</li><li>{isZh ? "在当前浏览器保存稍后读" : "Save for later in this browser"}</li><li>{isZh ? "查看自动处理说明" : "Inspect automated processing details"}</li></ul></section>
      <section className="tool-panel"><p className="section-eyebrow">{isZh ? "待验证假设" : "Hypothesis to validate"}</p><h2 className="section-title mt-1">Pro</h2><ul className="feature-list"><li>{isZh ? "跨设备收藏与个性化早报" : "Cross-device saves and personal briefs"}</li><li>{isZh ? "更高伴读与分发配额" : "Higher companion and distribution limits"}</li><li>{isZh ? "功能、价格和付费意愿尚未验证" : "Scope, pricing, and willingness to pay remain unvalidated"}</li></ul></section>
    </div>
    <BillingPanel locale={locale} />
  </section>;
}
