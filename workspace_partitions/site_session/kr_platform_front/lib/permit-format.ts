/** Shared formatting utilities for permit calculator display values. */

/** Format field values (boolean, number, null) for Korean display. */
export function formatFieldValue(v: unknown): string {
  if (typeof v === "boolean") return v ? "보유" : "미보유";
  if (v == null) return "—";
  const n = Number(v);
  if (!Number.isNaN(n)) return n.toLocaleString("ko-KR");
  return String(v);
}
