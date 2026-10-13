"use client";

import { usePathname } from "next/navigation";
import { AccountMenu } from "./AccountMenu";
import { ThemeToggle } from "./ThemeToggle";

const labels = {
  en: { home: "Today", library: "Saved", brief: "Brief", more: "More", developers: "Developers", pricing: "Plans (test)", lang: "中文" },
  zh: { home: "今日精选", library: "收藏", brief: "早报", more: "更多", developers: "开发者", pricing: "方案（测试）", lang: "English" }
};

export function Header({ locale }: { locale: string }) {
  const pathname = usePathname();
  const t = labels[locale as "en" | "zh"] ?? labels.en;
  const nextLocale = locale === "zh" ? "en" : "zh";
  return (
    <header className="app-header">
      <div className="header-inner">
        <a href={`/${locale}`} className="brand" aria-label="CodePick home">
          <span className="brand-mark" aria-hidden="true">c<span>/</span>p</span>
          <span className="brand-wordmark">CodePick<span className="brand-caption">READ LESS. KNOW MORE.</span></span>
        </a>
        <nav className="primary-nav" aria-label={locale === "zh" ? "主导航" : "Primary navigation"}>
          <a className="nav-link" aria-current={pathname === `/${locale}` ? "page" : undefined} href={`/${locale}`}>{t.home}</a>
          <a className="nav-link" aria-current={pathname === `/${locale}/library` ? "page" : undefined} href={`/${locale}/library`}>{t.library}</a>
          <a className="nav-link" aria-current={pathname === `/${locale}/brief` ? "page" : undefined} href={`/${locale}/brief`}>{t.brief}</a>
          <details className="secondary-nav">
            <summary className="nav-link">{t.more}</summary>
            <div className="secondary-nav-menu"><a href={`/${locale}/developers`}>{t.developers}</a><a href={`/${locale}/pricing`}>{t.pricing}</a></div>
          </details>
        </nav>
        <div className="header-utilities">
          <ThemeToggle locale={locale} />
          <a className="secondary-button min-h-11 whitespace-nowrap px-3" href={`/${nextLocale}`}>{t.lang}</a>
          <AccountMenu locale={locale} />
        </div>
      </div>
    </header>
  );
}
