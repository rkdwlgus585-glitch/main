import Link from "next/link";
import type { LegacyListingSummary } from "@/lib/legacy-types";

export function ListingPreview({ listings }: { listings: LegacyListingSummary[] }) {
  return (
    <div className="listing-preview-grid">
      {listings.map((item) => (
        <article key={item.id} className="listing-preview-card">
          <div className="listing-preview-meta">
            <span>{item.id}</span>
            <span>{item.region || "지역 협의"}</span>
          </div>
          <h3>
            <Link href={`/mna/${encodeURIComponent(item.id)}`}>{item.title}</Link>
          </h3>
          <p>{item.headline || item.note || item.sectorLabel}</p>
          <dl>
            <div>
              <dt>업종</dt>
              <dd>{item.sectorLabel}</dd>
            </div>
            <div>
              <dt>시공 / 실적</dt>
              <dd>{item.capacityLabel} / {item.performance3Year}</dd>
            </div>
            <div>
              <dt>양도가</dt>
              <dd>{item.price || "협의"}</dd>
            </div>
          </dl>
        </article>
      ))}
    </div>
  );
}
