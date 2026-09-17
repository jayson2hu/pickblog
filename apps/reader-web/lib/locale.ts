import { notFound } from "next/navigation";

export const locales = ["en", "zh"] as const;
export type ReaderLocale = (typeof locales)[number];

export function isReaderLocale(locale: string): locale is ReaderLocale {
  return locales.includes(locale as ReaderLocale);
}

export function requireReaderLocale(locale: string): ReaderLocale {
  if (!isReaderLocale(locale)) notFound();
  return locale;
}
