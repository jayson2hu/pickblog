import "../globals.css";
import { ReactNode } from "react";
import { Header } from "../../components/Header";
import { requireReaderLocale } from "../../lib/locale";

export const metadata = { title: "CodePick", description: "Traceable engineering reading for bilingual developers." };

export function generateStaticParams() {
  return [{ locale: "en" }, { locale: "zh" }];
}

export default async function LocaleLayout({ children, params }: { children: ReactNode; params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const readerLocale = requireReaderLocale(locale);
  return (
    <html lang={readerLocale}>
      <body>
        <a className="skip-link" href="#main-content">{readerLocale === "zh" ? "跳到主要内容" : "Skip to content"}</a>
        <div className="shell">
          <Header locale={readerLocale} />
          <main className="page-frame" id="main-content">{children}</main>
          <footer className="app-footer">
            <p>CodePick · {readerLocale === "zh" ? "可追溯的工程阅读" : "Traceable engineering reading"}</p>
            <p>{readerLocale === "zh" ? "公开来源内容与自动分析会分别标注。" : "Public-source content and automated analysis are labeled separately."}</p>
          </footer>
        </div>
      </body>
    </html>
  );
}
