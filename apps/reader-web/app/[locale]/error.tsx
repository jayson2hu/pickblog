"use client";

export default function ReaderError({ retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return <section className="state-panel mx-auto max-w-2xl text-center">
    <p className="page-kicker">Reader unavailable · 阅读服务不可用</p>
    <h1 className="page-title mx-auto">The content service did not respond</h1>
    <p className="page-subtitle mx-auto">No demonstration articles were substituted. Retry after the upstream Reader/L2 service recovers.</p>
    <p className="mt-2 text-sm text-muted">当前没有回退到演示数据；请等待上游 Reader/L2 服务恢复后重试。</p>
    <button className="primary-button mt-6" type="button" onClick={() => retry()}>Retry · 重试</button>
  </section>;
}
