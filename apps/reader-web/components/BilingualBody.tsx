"use client";

import { useState } from "react";
import { ContentDetail } from "../lib/api";
import { safeExternalUrl } from "../lib/presentation";

export function BilingualBody({ item, locale }: { item: ContentDetail; locale: string }) {
  const translated = item.translations?.zh;
  const translationAvailable = item.provenance?.translation_available === true && Boolean(translated);
  const [mode, setMode] = useState<"compare" | "source" | "zh">(translationAvailable && locale === "zh" ? "compare" : "source");
  const paragraphs = item.paragraphs ?? [];
  const isZh = locale === "zh";
  const fixtureTranslation = item.provenance?.source_kind === "fixture" || item.provenance?.scoring_method === "simulated";
  const extracted = item.provenance?.analysis_method?.startsWith("extractive-") === true;
  const sourceUrl = safeExternalUrl(item.provenance?.source_url ?? item.url);

  return (
    <section className="reading-section">
      <div className="section-heading-row">
        <div><p className="section-eyebrow">{isZh ? "发布者内容" : "Publisher material"}</p><h2 className="section-title">{isZh ? "原文摘录" : "Source excerpt"}</h2></div>
        {translationAvailable ? <div className="segmented" role="group" aria-label={isZh ? "摘录语言" : "Excerpt language"}>
          <button className={mode === "compare" ? "segment-active" : ""} type="button" onClick={() => setMode("compare")}>{isZh ? "对照" : "Compare"}</button>
          <button className={mode === "source" ? "segment-active" : ""} type="button" onClick={() => setMode("source")}>{isZh ? "原文" : "Source"}</button>
          <button className={mode === "zh" ? "segment-active" : ""} type="button" onClick={() => setMode("zh")}>中文</button>
        </div> : <span className="tag">{isZh ? "暂无译文" : "No translation stored"}</span>}
      </div>
      <p className="mt-3 text-sm leading-6 text-muted">
        {fixtureTranslation ? (isZh ? "当前摘录与译文来自测试样例，仅用于界面验收。" : "This excerpt and translation come from a fixture used for interface acceptance.")
          : extracted ? (isZh ? "摘录由公开来源抽取；上下文和完整表述请以发布者原文为准。" : "Extracted from the public source. Use the publisher source for complete context and wording.")
            : (isZh ? "当前摘录方法未确认；请以发布者原文为准。" : "The excerpt method is unverified. Use the publisher source as the authority.")}
      </p>
      {paragraphs.length ? <div className="mt-5 grid gap-4">{paragraphs.map((paragraph, index) => (
        <div className={mode === "compare" ? "bilingual-row" : "prose-block"} key={index}>
          {mode !== "zh" ? <p lang={item.language || "en"}>{paragraph.en}</p> : null}
          {translationAvailable && mode !== "source" ? <p lang="zh">{paragraph.zh}</p> : null}
        </div>
      ))}</div> : <div className="empty-inline">
        <p>{isZh ? "当前记录没有可展示的原文摘录。" : "No source excerpt is stored for this item."}</p>
        {sourceUrl ? <a href={sourceUrl} target="_blank" rel="noopener noreferrer">{isZh ? "前往发布者原文" : "Open the publisher source"}</a> : null}
      </div>}
    </section>
  );
}
