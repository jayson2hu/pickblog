"use client";

import type { ReactNode } from "react";
import { clientApiUrl } from "../lib/client-api";

export function TrackedContentLink({
  className,
  contentId,
  href,
  children
}: {
  className?: string;
  contentId: string;
  href: string;
  children: ReactNode;
}) {
  function trackClick() {
    const token = localStorage.getItem("codepick_token");
    if (!token) return;
    void fetch(clientApiUrl("/api/events"), {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ content_id: contentId, type: "click" }),
      keepalive: true
    }).catch(() => undefined);
  }

  return (
    <a className={className} href={href} onClick={trackClick}>
      {children}
    </a>
  );
}
