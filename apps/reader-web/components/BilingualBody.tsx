"use client";

import { useState } from "react";
import { ContentDetail } from "../lib/api";

export function BilingualBody({ item, locale }: { item: ContentDetail; locale: string }) {
  const [mode, setMode] = useState<"compare" | "en" | "zh">(locale === "zh" ? "compare" : "en");
  const zh = item.translations.zh;
  const paragraphs = item.paragraphs?.length
    ? item.paragraphs
    : [
        {
          en: item.base_analysis.summary,
          zh: zh?.base_analysis.summary ?? item.summary
        }
      ];

  return (
    <section className="tool-panel">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="section-title">{locale === "zh" ? "正文对照" : "Article body"}</h2>
        <div className="segmented" role="group" aria-label={locale === "zh" ? "正文语言" : "Body language"}>
          <button type="button" onClick={() => setMode("compare")}>
            {locale === "zh" ? "对照" : "Compare"}
          </button>
          <button type="button" onClick={() => setMode("en")}>
            EN
          </button>
          <button type="button" onClick={() => setMode("zh")}>
            中文
          </button>
        </div>
      </div>
      <div className="mt-5 grid gap-4">
        {paragraphs.map((paragraph, index) => (
          <div className={mode === "compare" ? "bilingual-row" : "prose-block"} key={index}>
            {mode !== "zh" ? <p>{paragraph.en}</p> : null}
            {mode !== "en" ? <p lang="zh">{paragraph.zh}</p> : null}
          </div>
        ))}
      </div>
    </section>
  );
}
