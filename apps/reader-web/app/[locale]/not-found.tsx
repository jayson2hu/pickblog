export default function NotFound() {
  return (
    <section className="state-panel mx-auto max-w-2xl text-center">
      <p className="page-kicker">404 · Not found</p>
      <h1 className="page-title mx-auto">这页不存在 / This page does not exist</h1>
      <p className="page-subtitle mx-auto">链接可能已失效，或语言路径不受支持。The link may be stale or the locale is unsupported.</p>
      <div className="mt-6 flex flex-wrap justify-center gap-3"><a className="primary-button" href="/zh">返回中文精选</a><a className="secondary-button" href="/en">Browse in English</a></div>
    </section>
  );
}
