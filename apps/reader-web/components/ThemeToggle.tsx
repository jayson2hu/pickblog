"use client";

import { useEffect, useState } from "react";

export function ThemeToggle({ locale }: { locale: string }) {
  const [theme, setTheme] = useState("light");

  useEffect(() => {
    const saved = localStorage.getItem("cp_theme");
    const initial = saved ?? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    setTheme(initial);
    document.documentElement.dataset.theme = initial;
  }, []);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.dataset.theme = next;
    localStorage.setItem("cp_theme", next);
  }

  return (
    <button className="icon-button" type="button" onClick={toggleTheme} aria-label={locale === "zh" ? "切换主题" : "Toggle theme"} title={locale === "zh" ? "切换主题" : "Toggle theme"}>
      {theme === "dark" ? "☀" : "☾"}
    </button>
  );
}
