import Link from "next/link";
import { siteConfig } from "@/components/site-config";

type BreadcrumbItem = {
  href: string;
  label: string;
};

export function Breadcrumbs({ items }: { items: BreadcrumbItem[] }) {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.label,
      item: `${siteConfig.host}${item.href}`,
    })),
  };

  return (
    <>
      <nav className="breadcrumb" aria-label="페이지 경로">
        {items.map((item, index) => (
          <span key={item.href}>
            {index > 0 ? <span className="breadcrumb-separator">/</span> : null}
            {index === items.length - 1 ? (
              <strong>{item.label}</strong>
            ) : (
              <Link href={item.href}>{item.label}</Link>
            )}
          </span>
        ))}
      </nav>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
    </>
  );
}
