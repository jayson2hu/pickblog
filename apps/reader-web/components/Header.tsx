import { AccountMenu } from "./AccountMenu";
import { ThemeToggle } from "./ThemeToggle";

const labels = {
  en: { home: "Reader", brief: "Brief", developers: "Developers", pricing: "Pricing", lang: "\u4e2d\u6587" },
  zh: { home: "\u9605\u8bfb", brief: "\u65e9\u62a5", developers: "\u5f00\u53d1\u8005", pricing: "\u8ba2\u9605", lang: "English" }
};

export function Header({ locale }: { locale: string }) {
  const t = labels[locale as "en" | "zh"] ?? labels.en;
  const nextLocale = locale === "zh" ? "en" : "zh";
  return (
    <header className="app-header">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-3">
        <a href={`/${locale}`} className="flex items-center gap-3" aria-label="CodePick home">
          <span className="grid h-9 w-9 place-items-center rounded-md bg-ink text-sm font-black text-white">CP</span>
          <span>
            <span className="block text-base font-bold tracking-normal">CodePick</span>
            <span className="hidden text-xs font-medium text-muted sm:block">L3 Reader & Distribution</span>
          </span>
        </a>
        <nav className="flex min-w-0 items-center gap-1 overflow-x-auto text-sm font-semibold text-muted" aria-label="Primary">
          <a className="nav-link" href={`/${locale}`}>
            {t.home}
          </a>
          <a className="nav-link" href={`/${locale}/brief`}>
            {t.brief}
          </a>
          <a className="nav-link" href={`/${locale}/developers`}>
            {t.developers}
          </a>
          <a className="nav-link" href={`/${locale}/pricing`}>
            {t.pricing}
          </a>
          <ThemeToggle locale={locale} />
          <a className="secondary-button min-h-11 whitespace-nowrap px-3" href={`/${nextLocale}`}>
            {t.lang}
          </a>
          <AccountMenu locale={locale} />
        </nav>
      </div>
    </header>
  );
}
