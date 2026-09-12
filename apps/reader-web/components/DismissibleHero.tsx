"use client";

import { ReactNode, useEffect, useState } from "react";

const key = "cp_hero_dismissed";

export function DismissibleHero({ children, locale }: { children: ReactNode; locale: string }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setVisible(Boolean(localStorage.getItem("codepick_token")) && localStorage.getItem(key) !== "true");
  }, []);

  if (!visible) return null;

  return (
    <div className="hero-shell">
      <button
        className="icon-button hero-dismiss"
        type="button"
        aria-label={locale === "zh" ? "关闭首页介绍" : "Dismiss hero"}
        onClick={() => {
          localStorage.setItem(key, "true");
          setVisible(false);
        }}
      >
        ×
      </button>
      {children}
    </div>
  );
}
