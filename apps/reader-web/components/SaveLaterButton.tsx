"use client";

import { useEffect, useState } from "react";

const key = "cp_saved";

function readSaved(): string[] {
  try {
    return JSON.parse(localStorage.getItem(key) ?? "[]");
  } catch {
    return [];
  }
}

export function SaveLaterButton({ contentId, locale }: { contentId: string; locale: string }) {
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setSaved(readSaved().includes(contentId));
  }, [contentId]);

  function toggle() {
    const current = readSaved();
    const next = current.includes(contentId) ? current.filter((id) => id !== contentId) : [contentId, ...current];
    localStorage.setItem(key, JSON.stringify(next));
    setSaved(next.includes(contentId));
  }

  return (
    <button className={saved ? "primary-button min-h-10" : "secondary-button min-h-10"} type="button" onClick={toggle}>
      {saved ? (locale === "zh" ? "已稍后读" : "Saved") : locale === "zh" ? "稍后读" : "Save later"}
    </button>
  );
}
