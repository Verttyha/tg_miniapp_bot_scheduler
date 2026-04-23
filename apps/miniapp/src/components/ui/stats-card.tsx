import { getUserDisplayName } from "../../lib/formatters";
import type { StatsEntry } from "../../types";

const ATTENDED_LABEL = "\u041f\u043e\u0441\u0435\u0442\u0438\u043b";
const MISSED_LABEL = "\u041f\u0440\u043e\u043f\u0443\u0441\u0442\u0438\u043b";
const INVITED_LABEL = "\u041f\u0440\u0438\u0433\u043b\u0430\u0448\u0435\u043d";

export function StatsCard({ entry }: { entry: StatsEntry }) {
  return (
    <article className="stats-card">
      <div className="stats-card__header">
        <strong>{getUserDisplayName(entry.user)}</strong>
        <span>{entry.attendance_rate}%</span>
      </div>
      <div className="stats-card__bar">
        <div className="stats-card__fill" style={{ width: `${entry.attendance_rate}%` }} />
      </div>
      <p>
        {ATTENDED_LABEL}: {entry.attended} | {MISSED_LABEL}: {entry.missed} | {INVITED_LABEL}: {entry.invited}
      </p>
    </article>
  );
}
