import { getUserDisplayName } from "../../lib/formatters";
import type { Workspace } from "../../types";

const DEFAULT_TITLE = "\u0423\u0447\u0430\u0441\u0442\u043d\u0438\u043a\u0438";
const SELECTED_SUFFIX = "\u0432\u044b\u0431\u0440\u0430\u043d\u043e";

interface ParticipantSelectorProps {
  members: Workspace["members"];
  selectedIds: number[];
  onToggle: (userId: number) => void;
  title?: string;
}

export function ParticipantSelector({
  members,
  selectedIds,
  onToggle,
  title = DEFAULT_TITLE
}: ParticipantSelectorProps) {
  return (
    <section className="participant-section">
      <div className="participant-section__header">
        <h2>{title}:</h2>
        <span>{selectedIds.length} {SELECTED_SUFFIX}</span>
      </div>

      <div className="participant-list">
        {members.map((member) => {
          const checked = selectedIds.includes(member.user.id);
          return (
            <label className="participant-item" key={member.id}>
              <span className={`participant-item__check ${checked ? "participant-item__check--active" : ""}`}>
                <input type="checkbox" checked={checked} onChange={() => onToggle(member.user.id)} />
              </span>
              <span>{getUserDisplayName(member.user)}</span>
            </label>
          );
        })}
      </div>
    </section>
  );
}
