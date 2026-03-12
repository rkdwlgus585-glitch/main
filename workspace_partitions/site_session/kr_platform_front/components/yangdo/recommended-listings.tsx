/** RecommendedListings — 비교 매물 그리드 */
import type { RecommendedListing } from "@/lib/yangdo-types";
import { Star } from "lucide-react";

interface RecommendedListingsProps {
  listings: RecommendedListing[];
}

export function RecommendedListings({ listings }: RecommendedListingsProps) {
  if (!listings.length) return null;

  return (
    <div className="yangdo-listings">
      <h4 className="yangdo-listings-title">비교 매물</h4>
      <div className="yangdo-listings-grid">
        {listings.map((item, i) => (
          <div key={i} className="calc-result-card yangdo-listing-card">
            <div className="yangdo-listing-header">
              <span className="yangdo-listing-name">{item.license_text ?? "매물"}</span>
              {item.score != null && (
                <span className="yangdo-listing-score">
                  <Star size={12} aria-hidden="true" />
                  {item.score}
                </span>
              )}
            </div>
            {item.price_eok != null && (
              <p className="yangdo-listing-price">{item.price_eok.toFixed(2)} 억원</p>
            )}
            {item.label && <span className="yangdo-listing-label">{item.label}</span>}
            {item.reason && <p className="yangdo-listing-reason">{item.reason}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
