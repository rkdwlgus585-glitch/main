export type LegacyListingSummary = {
  id: string;
  title: string;
  headline: string;
  updatedAt: string;
  status: string;
  sectors: string[];
  sectorLabel: string;
  region: string;
  companyType: string;
  companyYear: string;
  association: string;
  capital: string;
  balance: string;
  price: string;
  licenseYears: string[];
  capacityLabel: string;
  performance3Year: string;
  performance5Year: string;
  performance2025: string;
  note: string;
  sourceUrl: string;
};

export type LegacyListingDetail = LegacyListingSummary & {
  contentHtml: string;
  guidance: string[];
  legacyTitle: string;
  overview: Record<string, string>;
  performanceRows: string[][];
  finance: Record<string, string>;
  notes: string[];
};

export type LegacyBoardName = "notice" | "premium" | "news" | "tl_faq";

export type LegacyPost = {
  id: string;
  board: LegacyBoardName;
  title: string;
  summary: string;
  publishedAt: string;
  updatedAt: string;
  views: number | null;
  sourceUrl: string;
  contentHtml: string;
  faqItems?: FaqPreviewItem[];
};

export type LegacyPageGroup =
  | "registration"
  | "corporate"
  | "split-merger"
  | "practice"
  | "support"
  | "mna-info"
  | null;

export type LegacyPage = {
  slug: string;
  title: string;
  summary: string;
  contentHtml: string;
  updatedAt: string;
  sourceUrl: string;
  group: LegacyPageGroup;
};

export type FaqPreviewItem = {
  question: string;
  answer: string;
};
