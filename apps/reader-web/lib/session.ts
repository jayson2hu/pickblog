import { clientApiUrl } from "./client-api";

export type SessionProfile = {
  email: string;
  plan: string;
  is_admin: boolean;
  audience_code?: string;
};

export async function getMe(token?: string | null): Promise<SessionProfile | undefined> {
  if (!token) return undefined;
  try {
    const response = await fetch(clientApiUrl("/api/me"), { headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) throw new Error("me unavailable");
    const body = await response.json();
    return {
      email: body.email,
      plan: body.plan ?? "free",
      is_admin: body.is_admin === true,
      audience_code: body.audience_code
    };
  } catch {
    if (typeof window === "undefined") return undefined;
    return {
      email: localStorage.getItem("codepick_email") ?? "dev@example.com",
      plan: localStorage.getItem("codepick_plan") ?? "free",
      is_admin: localStorage.getItem("codepick_is_admin") === "true",
      audience_code: localStorage.getItem("codepick_audience") ?? "general"
    };
  }
}
