"use client";

import { useEffect, useState } from "react";
import type { ContentSummary } from "../lib/api";
import { hasSaved, setSaved } from "../lib/saved";

export function SaveLaterButton({ item, locale }: { item: ContentSummary; locale: string }) {
  const [saved, setSavedState] = useState(false);

  useEffect(() => {
    const refresh = () => setSavedState(hasSaved(item.id));
    refresh();
    window.addEventListener("codepick:saved-change", refresh);
    return () => window.removeEventListener("codepick:saved-change", refresh);
  }, [item.id]);

  function toggle() {
    const next = !saved;
    setSaved(item, next);
    setSavedState(next);
  }

  return (
    <button
      aria-pressed={saved}
      className={saved ? "primary-button min-h-10" : "secondary-button min-h-10"}
      title={locale === "zh" ? "保存在当前浏览器，可从收藏页回看" : "Saved in this browser and available from Saved"}
      type="button"
      onClick={toggle}
    >
      {saved ? (locale === "zh" ? "已存本机" : "Saved locally") : locale === "zh" ? "稍后读" : "Save for later"}
    </button>
  );
}
