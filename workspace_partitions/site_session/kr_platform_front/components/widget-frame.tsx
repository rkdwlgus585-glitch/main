"use client";

import { useState } from "react";

type WidgetFrameProps = {
  title: string;
  description: string;
  widgetUrl: string;
  openUrl?: string;
  eyebrow?: string;
  launchLabel?: string;
  gateNote?: string;
  defaultExpanded?: boolean;
};

export function WidgetFrame({
  title,
  description,
  widgetUrl,
  openUrl = "",
  eyebrow = "Widget launch",
  launchLabel = "Start widget",
  gateNote = "The external engine iframe is created only after the launch button is pressed.",
  defaultExpanded = false,
}: WidgetFrameProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <section className="widget-shell">
      <header className="widget-header">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
        {openUrl ? (
          <a className="widget-open" href={openUrl} target="_blank" rel="noreferrer noopener">
            {"전체 화면으로 열기"}
          </a>
        ) : null}
      </header>
      {!isExpanded ? (
        <div className="widget-gate" data-traffic-gate="closed">
          <p>{gateNote}</p>
          <button
            type="button"
            className="widget-launch-button"
            data-traffic-gate-launch="true"
            onClick={() => setIsExpanded(true)}
          >
            {launchLabel}
          </button>
        </div>
      ) : (
        <iframe
          data-traffic-gate="open"
          src={widgetUrl}
          title={title}
          style={{ width: "100%", minHeight: 1400, border: 0 }}
          sandbox="allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"
          allow="clipboard-write"
          loading="lazy"
          referrerPolicy="strict-origin-when-cross-origin"
        />
      )}
    </section>
  );
}
