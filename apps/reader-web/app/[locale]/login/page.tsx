import { InterestOnboarding } from "../../../components/InterestOnboarding";
import { LoginForm } from "../../../components/LoginForm";

export default async function LoginPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  return (
    <section className="grid gap-8">
      <header>
        <p className="page-kicker">{locale === "zh" ? "\u8d26\u6237" : "Account"}</p>
        <h1 className="page-title">{locale === "zh" ? "\u767b\u5f55" : "Login"}</h1>
        <p className="page-subtitle">
          {locale === "zh" ? "\u7ba1\u7406\u4f1a\u8bdd\u4e0e\u5174\u8da3\u3002Pro \u8ba2\u9605\u548c API \u5bc6\u94a5\u5df2\u5206\u522b\u79fb\u5230\u8ba2\u9605\u9875\u548c\u5f00\u53d1\u8005\u9875\u3002" : "Manage session and interests. Pro billing and API keys now live on Pricing and Developers."}
        </p>
      </header>
      <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="grid content-start gap-6">
          <LoginForm locale={locale} />
        </div>
        <div className="grid content-start gap-6">
          <InterestOnboarding locale={locale} />
          <section className="tool-panel">
            <h2 className="section-title">{locale === "zh" ? "\u5feb\u901f\u5165\u53e3" : "Shortcuts"}</h2>
            <div className="mt-3 flex flex-wrap gap-3">
              <a className="secondary-button" href={`/${locale}/pricing`}>
                {locale === "zh" ? "\u8ba2\u9605" : "Pricing"}
              </a>
              <a className="secondary-button" href={`/${locale}/developers`}>
                {locale === "zh" ? "API \u5bc6\u94a5" : "API keys"}
              </a>
            </div>
          </section>
        </div>
      </div>
    </section>
  );
}
