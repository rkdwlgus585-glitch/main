/**
 * Shared font loader for OG and Twitter image generation.
 *
 * Fetches Noto Sans KR Bold from Google Fonts with a 5-second timeout.
 * Falls back to system-ui when the CDN is unreachable.
 */

const FONT_URL =
  "https://fonts.gstatic.com/s/notosanskr/v39/PbyxFmXiEBPT4ITbgNA5Cgms3VYcOA-vvnIzzg01eLQ.ttf";

/** Fetch Noto Sans KR Bold; returns null on CDN failure. */
export async function loadOgFont(): Promise<ArrayBuffer | null> {
  try {
    return await fetch(FONT_URL, { signal: AbortSignal.timeout(5_000) }).then(
      (res) => res.arrayBuffer(),
    );
  } catch {
    /* CDN unreachable — render without custom font */
    return null;
  }
}

/** Build the font family CSS string: custom font when available, system-ui fallback. */
export function ogFontFamily(fontData: ArrayBuffer | null): string {
  return fontData ? "NotoSansKR" : "system-ui, sans-serif";
}

/** Build the ImageResponse fonts option from loaded font data. */
export function ogFontOption(fontData: ArrayBuffer | null): object {
  return fontData
    ? { fonts: [{ name: "NotoSansKR", data: fontData, weight: 700, style: "normal" as const }] }
    : {};
}
