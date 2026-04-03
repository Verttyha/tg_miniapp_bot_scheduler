import type { ReactNode } from "react";

interface LineFieldProps {
  label: string;
  children: ReactNode;
  multiline?: boolean;
}

export function LineField({ label, children, multiline = false }: LineFieldProps) {
  return (
    <label className={`line-field ${multiline ? "line-field--multiline" : ""}`}>
      <span>{label}:</span>
      <div className="line-field__control">{children}</div>
    </label>
  );
}
