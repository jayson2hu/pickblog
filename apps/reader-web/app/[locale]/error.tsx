"use client";

export default function ReaderError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <section className="tool-panel mx-auto max-w-2xl text-center">
      <p className="page-kicker">Reader unavailable</p>
      <h1 className="page-title">Content temporarily unavailable</h1>
      <p className="page-subtitle">The L2 content service could not be reached. Retry after the service recovers.</p>
      <p className="mt-2 text-sm text-muted">内容服务暂时不可用，请在上游恢复后重试。</p>
      <button className="primary-button mt-6" type="button" onClick={() => reset()}>
        Retry
      </button>
    </section>
  );
}
