import "../globals.css";
import { ReactNode } from "react";
import { Header } from "../../components/Header";

export const metadata = {
  title: "CodePick",
  description: "High-signal engineering reading, briefs, and API distribution."
};

export default function LocaleLayout({ children, params }: { children: ReactNode; params: { locale: string } }) {
  return (
    <html lang={params.locale}>
      <body>
        <div className="shell">
          <Header locale={params.locale} />
          <main className="page-frame">{children}</main>
        </div>
      </body>
    </html>
  );
}
