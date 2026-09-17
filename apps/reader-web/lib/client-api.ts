const configuredBase = process.env.NEXT_PUBLIC_READER_API_BASE?.trim();

export const clientApiBase = configuredBase ? configuredBase.replace(/\/+$/, "") : "";

export function clientApiUrl(path: string) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${clientApiBase}${normalizedPath}`;
}
