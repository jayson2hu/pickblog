import { SavedLibrary } from "../../../components/SavedLibrary";

export default async function LibraryPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const isZh = locale === "zh";
  return (
    <section className="grid gap-8">
      <header className="editorial-header">
        <div><p className="page-kicker">{isZh ? "稍后继续" : "Return to reading"}</p><h1 className="page-title">{isZh ? "我的收藏" : "Saved reading"}</h1>
          <p className="page-subtitle">{isZh ? "保留标题、来源链接和摘要快照，方便回到原文核对。当前游客收藏只保存在这台设备的浏览器。" : "Keep a title, source link, and summary snapshot so you can return to the original. Guest saves currently stay in this browser."}</p>
        </div>
      </header>
      <SavedLibrary locale={locale} />
    </section>
  );
}
