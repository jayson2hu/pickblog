import { AdminTaxonomyPanel } from "../../../components/admin/AdminTaxonomyPanel";

export default async function AdminPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const isZh = locale === "zh";
  return (
    <section className="grid gap-8">
      <header>
        <p className="page-kicker">{isZh ? "\u7ba1\u7406" : "Admin"}</p>
        <h1 className="page-title">{isZh ? "\u5206\u7c7b\u4e0e\u53d7\u4f17" : "Categories and audiences"}</h1>
        <p className="page-subtitle">{isZh ? "维护阅读端可见分类、受众标签和每个受众的分类集合。" : "Manage reader-visible categories, audience labels, and the category set assigned to each audience."}</p>
      </header>
      <AdminTaxonomyPanel locale={locale} />
    </section>
  );
}
