"use client";

import { FormEvent, useEffect, useState } from "react";

const apiBase = process.env.NEXT_PUBLIC_READER_API_BASE ?? "http://127.0.0.1:8000";

type Category = { code: string; label?: string; label_en: string; label_zh: string; color_from: string; color_to: string; active?: boolean; sort_order?: number };
type Audience = { code: string; label?: string; label_en: string; label_zh: string; is_default?: boolean; categories?: string[] };

const palettes = [
  ["#4f46e5", "#14b8a6"],
  ["#0f766e", "#2563eb"],
  ["#be123c", "#f59e0b"],
  ["#7c3aed", "#db2777"],
  ["#334155", "#10b981"]
];

const demoCategories: Category[] = [
  { code: "ai", label: "AI", label_en: "AI", label_zh: "AI", color_from: "#4f46e5", color_to: "#14b8a6" },
  { code: "data", label: "Data", label_en: "Data", label_zh: "数据", color_from: "#0f766e", color_to: "#2563eb" }
];

const copy = {
  en: {
    categoryManager: "Category manager",
    audienceManager: "Audience manager",
    code: "Code",
    english: "English label",
    chinese: "Chinese label",
    addCategory: "Add category",
    addAudience: "Add audience",
    save: "Save",
    delete: "Delete",
    noAccess: "No admin permission. Return to the reader home.",
    backHome: "Back home",
    local: "Local demo: sign in as admin and connect Reader API to save.",
    categorySaved: "Category saved",
    categoryFailed: "Category save failed",
    audienceSaved: "Audience saved",
    audienceFailed: "Audience save failed",
    deleteFailed: "Delete failed. The default or last audience cannot be deleted."
  },
  zh: {
    categoryManager: "分类管理",
    audienceManager: "受众管理",
    code: "代码",
    english: "英文名",
    chinese: "中文名",
    addCategory: "新增分类",
    addAudience: "新增受众",
    save: "保存",
    delete: "删除",
    noAccess: "无管理员权限。请返回首页。",
    backHome: "返回首页",
    local: "本地演示：使用 admin 账号并连接 Reader API 后可保存。",
    categorySaved: "分类已保存",
    categoryFailed: "分类保存失败",
    audienceSaved: "受众已保存",
    audienceFailed: "受众保存失败",
    deleteFailed: "删除失败。默认受众或最后一个受众不可删除。"
  }
};

function labelFor(item: Category | Audience, locale: string) {
  return locale === "zh" ? item.label_zh || item.label || item.code : item.label_en || item.label || item.code;
}

export function AdminTaxonomyPanel({ locale }: { locale: string }) {
  const isZh = locale === "zh";
  const t = copy[locale as "en" | "zh"] ?? copy.en;
  const [authorized, setAuthorized] = useState<boolean | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [audiences, setAudiences] = useState<Audience[]>([]);
  const [status, setStatus] = useState("");
  const [categoryForm, setCategoryForm] = useState({ code: "ops", label_en: "Operations", label_zh: "运营", palette: 0 });
  const [audienceForm, setAudienceForm] = useState({ code: "operators", label_en: "Operators", label_zh: "运营者" });

  async function request(path: string, init?: RequestInit) {
    const token = localStorage.getItem("codepick_token");
    const response = await fetch(`${apiBase}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token ?? ""}`, ...(init?.headers ?? {}) }
    });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  }

  async function loadTaxonomy() {
    const body = await request("/api/admin/taxonomy");
    setCategories(body.categories ?? []);
    setAudiences(body.audiences ?? []);
  }

  useEffect(() => {
    async function boot() {
      try {
        const me = await request("/api/me");
        if (me.is_admin !== true) {
          setAuthorized(false);
          return;
        }
        setAuthorized(true);
        await loadTaxonomy();
      } catch {
        const demoAdmin = localStorage.getItem("codepick_is_admin") === "true";
        setAuthorized(demoAdmin);
        if (demoAdmin) {
          setCategories(demoCategories);
          setAudiences([{ code: "general", label: isZh ? "通用读者" : "General readers", label_en: "General readers", label_zh: "通用读者", is_default: true, categories: ["ai"] }]);
          setStatus(t.local);
        }
      }
    }
    void boot();
  }, []);

  async function createCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const [color_from, color_to] = palettes[categoryForm.palette] ?? palettes[0];
    try {
      await request("/api/admin/categories", {
        method: "POST",
        body: JSON.stringify({ code: categoryForm.code, label_en: categoryForm.label_en, label_zh: categoryForm.label_zh, color_from, color_to })
      });
      setStatus(t.categorySaved);
      await loadTaxonomy();
    } catch {
      setStatus(t.categoryFailed);
    }
  }

  async function patchCategory(category: Category) {
    try {
      await request(`/api/admin/categories/${category.code}`, { method: "PATCH", body: JSON.stringify(category) });
      setStatus(t.categorySaved);
      await loadTaxonomy();
    } catch {
      setStatus(t.categoryFailed);
    }
  }

  async function deleteCategory(code: string) {
    try {
      await request(`/api/admin/categories/${code}`, { method: "DELETE" });
      setStatus(t.categorySaved);
      await loadTaxonomy();
    } catch {
      setStatus(t.categoryFailed);
    }
  }

  async function createAudience(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await request("/api/admin/audiences", { method: "POST", body: JSON.stringify(audienceForm) });
      setStatus(t.audienceSaved);
      await loadTaxonomy();
    } catch {
      setStatus(t.audienceFailed);
    }
  }

  async function patchAudience(audience: Audience) {
    try {
      await request(`/api/admin/audiences/${audience.code}`, { method: "PATCH", body: JSON.stringify(audience) });
      setStatus(t.audienceSaved);
      await loadTaxonomy();
    } catch {
      setStatus(t.audienceFailed);
    }
  }

  async function deleteAudience(code: string) {
    try {
      await request(`/api/admin/audiences/${code}`, { method: "DELETE" });
      setStatus(t.audienceSaved);
      await loadTaxonomy();
    } catch {
      setStatus(t.deleteFailed);
    }
  }

  async function toggleAudienceCategory(audience: Audience, categoryCode: string) {
    const current = new Set(audience.categories ?? []);
    if (current.has(categoryCode)) current.delete(categoryCode);
    else current.add(categoryCode);
    try {
      await request(`/api/admin/audiences/${audience.code}/categories`, { method: "PUT", body: JSON.stringify({ categories: [...current] }) });
      setStatus(t.audienceSaved);
      await loadTaxonomy();
    } catch {
      setStatus(t.audienceFailed);
    }
  }

  if (authorized === false) {
    return (
      <section className="tool-panel">
        <h2 className="section-title">{t.noAccess}</h2>
        <a className="secondary-button mt-4" href={`/${locale}`}>
          {t.backHome}
        </a>
      </section>
    );
  }

  return (
    <div className="grid gap-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="tool-panel">
          <h2 className="section-title">{t.categoryManager}</h2>
          <form className="mt-4 grid gap-3" onSubmit={createCategory}>
            <div className="grid gap-3 sm:grid-cols-3">
              <input className="rounded-md border border-line bg-white px-3 py-2 text-ink" value={categoryForm.code} onChange={(event) => setCategoryForm({ ...categoryForm, code: event.target.value })} aria-label={isZh ? "分类 code" : "Category code"} />
              <input className="rounded-md border border-line bg-white px-3 py-2 text-ink" value={categoryForm.label_en} onChange={(event) => setCategoryForm({ ...categoryForm, label_en: event.target.value })} aria-label={t.english} />
              <input className="rounded-md border border-line bg-white px-3 py-2 text-ink" value={categoryForm.label_zh} onChange={(event) => setCategoryForm({ ...categoryForm, label_zh: event.target.value })} aria-label={t.chinese} />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {palettes.map(([from, to], index) => (
                <button key={`${from}-${to}`} className={`swatch${categoryForm.palette === index ? " swatch-active" : ""}`} type="button" style={{ background: `linear-gradient(135deg, ${from}, ${to})` }} onClick={() => setCategoryForm({ ...categoryForm, palette: index })} aria-label={`Palette ${index + 1}`} />
              ))}
              <button className="primary-button" type="submit">
                {t.addCategory}
              </button>
            </div>
          </form>
          <div className="mt-4 grid gap-3">
            {categories.map((category) => (
              <div className="admin-row" key={category.code}>
                <span className="swatch" style={{ background: `linear-gradient(135deg, ${category.color_from}, ${category.color_to})` }} />
                <input className="admin-input" value={category.label_en} onChange={(event) => setCategories((current) => current.map((item) => (item.code === category.code ? { ...item, label_en: event.target.value } : item)))} aria-label={`${category.code} ${t.english}`} />
                <input className="admin-input" value={category.label_zh} onChange={(event) => setCategories((current) => current.map((item) => (item.code === category.code ? { ...item, label_zh: event.target.value } : item)))} aria-label={`${category.code} ${t.chinese}`} />
                <code className="text-sm text-muted">{category.code}</code>
                <button className="secondary-button" type="button" onClick={() => patchCategory(category)}>
                  {t.save}
                </button>
                <button className="secondary-button" type="button" onClick={() => deleteCategory(category.code)}>
                  {t.delete}
                </button>
              </div>
            ))}
          </div>
        </section>

        <section className="tool-panel">
          <h2 className="section-title">{t.audienceManager}</h2>
          <form className="mt-4 grid gap-3" onSubmit={createAudience}>
            <div className="grid gap-3 sm:grid-cols-3">
              <input className="rounded-md border border-line bg-white px-3 py-2 text-ink" value={audienceForm.code} onChange={(event) => setAudienceForm({ ...audienceForm, code: event.target.value })} aria-label={isZh ? "受众 code" : "Audience code"} />
              <input className="rounded-md border border-line bg-white px-3 py-2 text-ink" value={audienceForm.label_en} onChange={(event) => setAudienceForm({ ...audienceForm, label_en: event.target.value })} aria-label={`${t.audienceManager} ${t.english}`} />
              <input className="rounded-md border border-line bg-white px-3 py-2 text-ink" value={audienceForm.label_zh} onChange={(event) => setAudienceForm({ ...audienceForm, label_zh: event.target.value })} aria-label={`${t.audienceManager} ${t.chinese}`} />
            </div>
            <button className="primary-button justify-self-start" type="submit">
              {t.addAudience}
            </button>
          </form>
          <div className="mt-4 grid gap-3">
            {audiences.map((audience) => (
              <div className="audience-card" key={audience.code}>
                <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto_auto_auto] sm:items-center">
                  <input className="admin-input" value={audience.label_en} onChange={(event) => setAudiences((current) => current.map((item) => (item.code === audience.code ? { ...item, label_en: event.target.value } : item)))} aria-label={`${audience.code} ${t.english}`} />
                  <input className="admin-input" value={audience.label_zh} onChange={(event) => setAudiences((current) => current.map((item) => (item.code === audience.code ? { ...item, label_zh: event.target.value } : item)))} aria-label={`${audience.code} ${t.chinese}`} />
                  <code className="text-sm text-muted">{audience.code}</code>
                  <button className="secondary-button" type="button" onClick={() => patchAudience(audience)}>
                    {t.save}
                  </button>
                  <button className="secondary-button" type="button" onClick={() => deleteAudience(audience.code)}>
                    {t.delete}
                  </button>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {categories.map((category) => {
                    const checked = (audience.categories ?? []).includes(category.code);
                    return (
                      <button className={`chip${checked ? " chip-active" : ""}`} type="button" key={category.code} onClick={() => toggleAudienceCategory(audience, category.code)}>
                        {labelFor(category, locale)}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
      {status ? <p className="text-sm font-semibold text-accent">{status}</p> : null}
    </div>
  );
}
