import { Link } from "react-router-dom";

interface ProviderLinkCardProps {
  provider: "google" | "yandex";
  isActive: boolean;
  to: string;
}

export function ProviderLinkCard({ provider, isActive, to }: ProviderLinkCardProps) {
  const providerLabel = provider === "google" ? "Google" : "Yandex";

  return (
    <Link
      className={`provider-card ${isActive ? "provider-card--active" : "provider-card--inactive"}`}
      to={to}
    >
      <span className={`provider-card__dot provider-card__dot--${provider}`} />
      <span>{providerLabel}</span>
    </Link>
  );
}
