import { ConsultationCTA } from "@/components/consultation-cta";
import { HomeHero } from "@/components/home-hero";
import { HomeMarketPreview } from "@/components/home-market-preview";
import { HomeOperations } from "@/components/home-operations";
import { HomeProcess } from "@/components/home-process";
import { HomeShortcuts } from "@/components/home-shortcuts";
import { PlatformStatus } from "@/components/platform-status";

export default function HomePage() {
  return (
    <main className="page-shell page-shell--home">
      <PlatformStatus />
      <HomeHero />
      <HomeShortcuts />
      <HomeMarketPreview />
      <HomeOperations />
      <HomeProcess />
      <ConsultationCTA />
    </main>
  );
}
