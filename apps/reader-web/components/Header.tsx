import { AccountMenu } from "./AccountMenu";
import { ThemeToggle } from "./ThemeToggle";

const labels = {
  en: { home: "Today", library: "Saved", brief: "Brief", more: "More", developers: "Developers", pricing: "Plans (test)", lang: "中文" },
  zh: { home: "今日精选", library: "收藏", brief: "早报", more: "更多", developers: "开发者", pricing: "方案（测试）", lang: "English" }
};

export function Header({ locale }: { locale: string }) {
  const t = labels[locale as "en" | "zh"] ?? labels.en;
  const nextLocale = locale === "zh" ? "en" : "zh";
  return (
    <header className="app-header">
      <div className="header-inner">
        <a href={`/${locale}`} className="flex items-center gap-3" aria-label="CodePick home">
          <span className="brand-mark" aria-hidden="true">CP</span>
          <span><span className="block text-base font-bold tracking-normal">CodePick</span><span className="hidden text-xs font-medium text-muted sm:block">{locale === "zh" ? "工程阅读工作台" : "Engineering reading desk"}</span></span>
        </a>
        <nav className="primary-nav" aria-label={locale === "zh" ? "主导航" : "Primary navigation"}>
          <a className="nav-link" href={`/${locale}`}>{t.home}</a>
          <a className="nav-link" href={`/${locale}/library`}>{t.library}</a>
          <a className="nav-link" href={`/${locale}/brief`}>{t.brief}</a>
          <details className="secondary-nav">
            <summary className="nav-link">{t.more}</summary>
            <div className="secondary-nav-menu"><a href={`/${locale}/developers`}>{t.developers}</a><a href={`/${locale}/pricing`}>{t.pricing}</a></div>
          </details>
          <ThemeToggle locale={locale} />
          <a className="secondary-button min-h-11 whitespace-nowrap px-3" href={`/${nextLocale}`}>{t.lang}</a>
          <AccountMenu locale={locale} />
        </nav>
      </div>
    </header>
  );
}
