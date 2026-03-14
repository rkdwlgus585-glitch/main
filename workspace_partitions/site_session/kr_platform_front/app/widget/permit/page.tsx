import type { Metadata } from "next";
import { Suspense } from "react";
import { PermitCalculator } from "@/components/permit/permit-calculator";
import { WidgetBranding } from "@/components/widget-branding";

export const metadata: Metadata = {
  title: "AI 인허가 검토",
  robots: { index: false, follow: false },
};

export default function PermitWidgetPage() {
  return (
    <main className="widget-shell">
      <Suspense fallback={<div className="widget-loading" aria-busy="true"><div className="calc-skeleton" style={{ height: 400 }} /></div>}>
        <PermitCalculator />
      </Suspense>
      <WidgetBranding />
    </main>
  );
}
