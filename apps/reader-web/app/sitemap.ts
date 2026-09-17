import { MetadataRoute } from "next";
import { getFeed } from "../lib/api";

const siteUrl = (process.env.NEXT_PUBLIC_SITE_URL ?? "https://codepick.example").replace(/\/$/, "");
const locales = ["en", "zh"];
export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const items = await getFeed();
  const routeEntries = locales.flatMap((locale) => [
    { url: `${siteUrl}/${locale}`, lastModified: now },
    { url: `${siteUrl}/${locale}/brief`, lastModified: now },
    { url: `${siteUrl}/${locale}/library`, lastModified: now }
  ]);
  const itemEntries = items.flatMap((item) => locales.map((locale) => ({
    url: `${siteUrl}/${locale}/items/${item.id}`,
    ...(item.published_at ? { lastModified: new Date(item.published_at) } : {})
  })));
  return [...routeEntries, ...itemEntries];
}
