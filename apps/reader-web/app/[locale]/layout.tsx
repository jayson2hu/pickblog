import "../globals.css";
import { ReactNode } from "react";
import { Header } from "../../components/Header";

export const metadata = {
  title: "CodePick",
  description: "High-signal engineering reading, briefs, and API distribution."
};

export default async function LocaleLayout({ children, params }: { children: ReactNode; params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  return (
    <html lang={locale}>
      <body>
        <div className="shell">
          <Header locale={locale} />
          <main className="page-frame">{children}</main>
        </div>
      </body>
    </html>
  );
}
