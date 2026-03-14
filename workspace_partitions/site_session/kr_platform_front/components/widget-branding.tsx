import { platformConfig } from "@/components/platform-config";

export function WidgetBranding() {
  return (
    <div className="widget-branding">
      <span className="widget-branding-logo">서울건설정보</span>
      <span className="widget-branding-sep" aria-hidden="true">&middot;</span>
      <a
        href={`${platformConfig.platformFrontHost}/partners`}
        target="_blank"
        rel="noopener noreferrer"
        className="widget-branding-cta"
      >
        시스템 도입 문의
      </a>
    </div>
  );
}
