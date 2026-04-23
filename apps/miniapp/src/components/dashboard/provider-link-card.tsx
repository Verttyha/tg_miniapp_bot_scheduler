import { Link } from "react-router-dom";

interface ProviderLinkCardProps {
  provider: "google" | "yandex";
  isActive: boolean;
  isDisabled?: boolean;
  to: string;
}

export function ProviderLinkCard({ provider, isActive, isDisabled = false, to }: ProviderLinkCardProps) {
  const providerLabel = provider === "google" ? "Google" : "Yandex";
  const className = [
    "provider-card",
    isDisabled ? "provider-card--disabled" : isActive ? "provider-card--active" : "provider-card--inactive",
  ].join(" ");
  const dotClass = `provider-card__dot ${
    isDisabled ? "provider-card__dot--disabled" : isActive ? "provider-card__dot--active" : "provider-card__dot--inactive"
  }`;

  if (isDisabled) {
    return (
      <span className={className} aria-disabled="true">
        <span className={dotClass} />
        <span>{providerLabel}</span>
      </span>
    );
  }

  return (
    <Link
      className={className}
      to={to}
    >
      <span className={dotClass} />
      <span>{providerLabel}</span>
    </Link>
  );
}
