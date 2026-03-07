import Link from "next/link";

type ProductCardProps = {
  href: string;
  badge: string;
  title: string;
  description: string;
  bullets: string[];
};

export function ProductCard({ href, badge, title, description, bullets }: ProductCardProps) {
  return (
    <article className="product-card">
      <p className="product-badge">{badge}</p>
      <h2>{title}</h2>
      <p className="product-description">{description}</p>
      <ul>
        {bullets.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      <Link className="product-link" href={href}>
        {"\uc2dc\uc2a4\ud15c \uc5f4\uae30"}
      </Link>
    </article>
  );
}
