"use client";

import { useEffect, useState } from "react";
import { clientApiUrl } from "../lib/client-api";


const requestTimeoutMs = 2500;

type ApiKeyRecord = {
  prefix: string;
  scopes: string[];
  rate_limit_rpm: number;
  daily_quota: number;
  status: string;
  key?: string;
};

const localStorageKey = "codepick_api_keys";

function localKeys(): ApiKeyRecord[] {
  try {
    return JSON.parse(localStorage.getItem(localStorageKey) ?? "[]");
  } catch {
    return [];
  }
}

function saveLocalKeys(keys: ApiKeyRecord[]) {
  localStorage.setItem(localStorageKey, JSON.stringify(keys));
}

function localDemoKey(): ApiKeyRecord {
  const raw = `cp_demo_${Math.random().toString(36).slice(2, 12)}`;
  return { key: raw, prefix: raw.slice(0, 8), scopes: ["read"], rate_limit_rpm: 20, daily_quota: 200, status: "active" };
}

export function ApiKeyPanel({ locale }: { locale: string }) {
  const [keys, setKeys] = useState<ApiKeyRecord[]>([]);
  const [createdKey, setCreatedKey] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("codepick_token");
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), requestTimeoutMs);
    fetch(clientApiUrl("/api/api-keys"), { headers: { Authorization: `Bearer ${token ?? ""}` }, signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("api unavailable");
        return response.json();
      })
      .then((body) => setKeys(body.items ?? []))
      .catch(() => setKeys(localKeys()))
      .finally(() => window.clearTimeout(timeout));
  }, []);

  async function createKey() {
    const token = localStorage.getItem("codepick_token");
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), requestTimeoutMs);
    try {
      const response = await fetch(clientApiUrl("/api/api-keys"), {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token ?? ""}` },
        body: JSON.stringify({ scopes: ["read"] }),
        signal: controller.signal
      });
      if (!response.ok) throw new Error("api unavailable");
      const body = await response.json();
      setCreatedKey(body.key);
      setKeys((current) => [body, ...current]);
      setStatus(locale === "zh" ? "\u5df2\u521b\u5efa API \u5bc6\u94a5" : "API key created");
    } catch {
      const body = localDemoKey();
      const next = [body, ...localKeys()];
      saveLocalKeys(next);
      setKeys(next);
      setCreatedKey(body.key ?? "");
      setStatus(locale === "zh" ? "\u5df2\u521b\u5efa\u672c\u5730\u6f14\u793a API \u5bc6\u94a5" : "Local demo API key created");
    } finally {
      window.clearTimeout(timeout);
    }
  }

  async function revokeKey(key: ApiKeyRecord) {
    const isLocalDemo = key.key?.startsWith("cp_demo_") === true || key.prefix.startsWith("cp_demo_");
    if (isLocalDemo) {
      const update = (item: ApiKeyRecord) => (item.prefix === key.prefix ? { ...item, status: "revoked" } : item);
      saveLocalKeys(localKeys().map(update));
      setKeys((current) => current.map(update));
      setStatus(locale === "zh" ? "本地演示 API 密钥已撤销" : "Local demo API key revoked");
      return;
    }

    const token = localStorage.getItem("codepick_token");
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), requestTimeoutMs);
    try {
      const response = await fetch(clientApiUrl(`/api/api-keys/${key.prefix}`), {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token ?? ""}` },
        signal: controller.signal
      });
      if (!response.ok) throw new Error("api unavailable");
      setKeys((current) => current.map((item) => (item.prefix === key.prefix ? { ...item, status: "revoked" } : item)));
      setStatus(locale === "zh" ? "API 密钥已撤销" : "API key revoked");
    } catch {
      setStatus(locale === "zh" ? "API 密钥未撤销；Reader API 拒绝了请求，请重试。" : "API key was not revoked. The Reader API rejected the request; try again.");
    } finally {
      window.clearTimeout(timeout);
    }
  }

  return (
    <section id="api-keys" className="tool-panel">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="section-title">{locale === "zh" ? "Public API \u5bc6\u94a5" : "Public API keys"}</h2>
          <p className="mt-1 text-sm text-muted">{locale === "zh" ? "\u901a\u8fc7 X-API-Key \u8c03\u7528 /v1 \u5206\u53d1\u63a5\u53e3\u3002" : "Use X-API-Key for /v1 distribution endpoints."}</p>
        </div>
        <button className="primary-button" onClick={createKey}>
          {locale === "zh" ? "\u521b\u5efa\u5bc6\u94a5" : "Create key"}
        </button>
      </div>
      {createdKey ? (
        <p className="mt-3 break-all rounded-md bg-panel px-3 py-2 text-sm font-semibold text-accent">
          {locale === "zh" ? "\u65b0\u5bc6\u94a5\uff1a" : "New key:"} {createdKey}
        </p>
      ) : null}
      {status ? <p className="mt-3 text-sm text-muted">{status}</p> : null}
      <div className="mt-4 grid gap-2">
        {keys.length === 0 ? <p className="text-sm text-muted">{locale === "zh" ? "\u6682\u65e0 API \u5bc6\u94a5" : "No API keys yet"}</p> : null}
        {keys.map((key) => (
          <div key={key.prefix} className="flex flex-col gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm sm:flex-row sm:items-center sm:justify-between">
            <span>
              <strong>{key.prefix}</strong> / {key.status} / {key.daily_quota}/day / {key.rate_limit_rpm}/min
            </span>
            {key.status === "active" ? (
              <button className="secondary-button min-h-8 px-3 py-1 text-sm" onClick={() => revokeKey(key)}>
                {locale === "zh" ? "\u64a4\u9500" : "Revoke"}
              </button>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}
