import Link from "next/link";
import { platformConfig } from "@/components/platform-config";

export function Hero() {
  return (
    <section className="hero-shell">
      <div className="hero-copy">
        <p className="eyebrow">AI M&amp;A and Permit Platform</p>
        <h1>
          {"\uc591\ub3c4\uac00 \uc0b0\uc815\uacfc \uc778\ud5c8\uac00 \uc0ac\uc804\uac80\ud1a0\ub97c \ud558\ub098\uc758 \ud50c\ub7ab\ud3fc \uc785\uad6c\uc5d0\uc11c \uc5f0\uacb0\ud569\ub2c8\ub2e4"}
        </h1>
        <p className="hero-body">
          {`${platformConfig.brandName}\ub294 \uacf5\uac1c \ud50c\ub7ab\ud3fc \uc804\uba74\uc5d0\uc11c \uc0c1\ub2f4 \uc785\uad6c\ub97c \ud1b5\ud569\ud558\uace0, \ube44\uacf5\uac1c \uc5d4\uc9c4\uc5d0\uc11c \uc2e4\uc81c \uacc4\uc0b0\uacfc \ud310\uc815\uc744 \ucc98\ub9ac\ud569\ub2c8\ub2e4. seoulmna.co.kr\uc740 \uc591\ub3c4\uc591\uc218 \ub9e4\ubb3c \uc0ac\uc774\ud2b8 \uc5ed\ud560\uc5d0 \uc9d1\uc911\ud558\uace0, \uacc4\uc0b0\uae30 \uacf5\uac1c \ub178\ucd9c\uc740 seoulmna.kr/_calc/* \uacbd\ub85c\uc5d0\uc11c\ub9cc \uc774\ub8e8\uc5b4\uc9d1\ub2c8\ub2e4.`}
        </p>
        <div className="hero-actions">
          <Link className="primary" href="/yangdo">
            {"\uc591\ub3c4\uac00 \uc0b0\uc815 \ubc14\ub85c \uc2dc\uc791"}
          </Link>
          <Link className="secondary" href="/permit">
            {"\uc778\ud5c8\uac00 \uc0ac\uc804\uac80\ud1a0 \ubc14\ub85c \uc9c4\uc785"}
          </Link>
        </div>
      </div>
      <div className="hero-panel">
        <div className="metric-card">
          <span>{"\ud50c\ub7ab\ud3fc \uc804\uba74"}</span>
          <strong>seoulmna.kr</strong>
        </div>
        <div className="metric-card">
          <span>{"\ub9e4\ubb3c \uc0ac\uc774\ud2b8"}</span>
          <strong>seoulmna.co.kr</strong>
        </div>
        <div className="metric-card">
          <span>{"\ube44\uacf5\uac1c \uacc4\uc0b0 \uc5d4\uc9c4"}</span>
          <strong>{"\ub0b4\ubd80 \uc804\uc6a9"}</strong>
        </div>
      </div>
    </section>
  );
}
