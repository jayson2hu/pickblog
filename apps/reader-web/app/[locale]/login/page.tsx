import { InterestOnboarding } from "../../../components/InterestOnboarding";
import { LoginForm } from "../../../components/LoginForm";

export default async function LoginPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const isZh = locale === "zh";
  return <section className="grid gap-8">
    <header className="editorial-header">
      <div><p className="page-kicker">{isZh ? "本机验收身份" : "Local acceptance identity"}</p><h1 className="page-title">{isZh ? "登录" : "Login"}</h1><p className="page-subtitle">{isZh ? "当前页面创建本机开发会话，用于验证收藏、兴趣和权限界面；它不代表生产认证或真实订阅。" : "This page creates a local development session for bookmark, interest, and permission workflows. It is not production authentication or a real subscription."}</p></div>
      <div className="trust-note"><p className="metric-label">{isZh ? "数据范围" : "Data boundary"}</p><p>{isZh ? "会话信息保存在当前浏览器；请勿输入真实密码或敏感账号。" : "Session details stay in this browser. Do not enter a real password or sensitive account."}</p></div>
    </header>
    <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]"><LoginForm locale={locale} /><InterestOnboarding locale={locale} /></div>
  </section>;
}
