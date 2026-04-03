import { Link } from "react-router-dom";

const BACK_LABEL = "\u041d\u0430\u0437\u0430\u0434";

interface ScreenHeaderProps {
  backTo?: string;
  eyebrow?: string;
  title: string;
  description?: string;
}

export function ScreenHeader({ backTo, eyebrow, title, description }: ScreenHeaderProps) {
  return (
    <header className="screen-header">
      {backTo ? (
        <Link className="screen-header__back" to={backTo}>
          {BACK_LABEL}
        </Link>
      ) : null}
      {eyebrow ? <p className="screen-header__eyebrow">{eyebrow}</p> : null}
      <h1 className="screen-header__title">{title}</h1>
      {description ? <p className="screen-header__description">{description}</p> : null}
    </header>
  );
}
