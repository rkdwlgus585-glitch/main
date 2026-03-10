"use client";

import { MessageCircleMore, Phone } from "lucide-react";
import { ContactLink } from "@/components/contact-link";
import { siteConfig } from "@/components/site-config";

export function StickyContactBar() {
  return (
    <div className="sticky-contact-bar" aria-label="빠른 상담">
      <ContactLink
        href={`tel:${siteConfig.phone}`}
        className="sticky-contact-button sticky-contact-button--phone"
        eventName="click_phone"
        eventLabel="sticky_phone"
      >
        <Phone size={16} aria-hidden="true" />
        전화상담
      </ContactLink>
      <ContactLink
        href={siteConfig.kakaoUrl}
        className="sticky-contact-button sticky-contact-button--kakao"
        eventName="click_kakao"
        eventLabel="sticky_kakao"
        newTab
      >
        <MessageCircleMore size={16} aria-hidden="true" />
        카카오 문의
      </ContactLink>
    </div>
  );
}
