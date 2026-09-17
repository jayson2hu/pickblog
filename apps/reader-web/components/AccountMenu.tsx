"use client";

import { useEffect, useState } from "react";
import { getMe, SessionProfile } from "../lib/session";

export function AccountMenu({ locale }: { locale: string }) {
  const [session, setSession] = useState<SessionProfile | undefined>();
  useEffect(() => { const token = localStorage.getItem("codepick_token"); void getMe(token).then(setSession); }, []);
  if (!session) return <a className="secondary-button min-h-11" href={`/${locale}/login`}>{locale === "zh" ? "登录" : "Login"}</a>;

  return <details className="account-menu"><summary aria-label={locale === "zh" ? "账户菜单" : "Account menu"}><span className="avatar">{session.email.slice(0, 1).toUpperCase()}</span><span className="hidden sm:inline">{session.plan === "pro" ? "Test Pro" : "Local"}</span></summary>
    <div className="account-popover"><p className="text-sm font-semibold text-ink">{session.email}</p><p className="text-xs text-muted">{locale === "zh" ? "本机开发会话" : "Local development session"}</p><a href={`/${locale}/library`}>{locale === "zh" ? "我的收藏" : "Saved reading"}</a><a href={`/${locale}/brief`}>{locale === "zh" ? "公共早报" : "Public brief"}</a><a href={`/${locale}/pricing`}>{locale === "zh" ? "方案原型" : "Plan prototype"}</a><a href={`/${locale}/developers`}>{locale === "zh" ? "开发者工具" : "Developer tools"}</a>{session.is_admin ? <a href={`/${locale}/admin`}>{locale === "zh" ? "管理后台" : "Admin"}</a> : null}
      <button type="button" onClick={() => { localStorage.removeItem("codepick_token"); localStorage.removeItem("codepick_plan"); localStorage.removeItem("codepick_email"); localStorage.removeItem("codepick_is_admin"); window.location.href = `/${locale}`; }}>{locale === "zh" ? "退出本机会话" : "End local session"}</button>
    </div>
  </details>;
}
