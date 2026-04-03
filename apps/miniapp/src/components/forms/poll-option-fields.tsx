const OPTIONS_TITLE = "\u0412\u0430\u0440\u0438\u0430\u043d\u0442\u044b";
const ADD_OPTION_LABEL = "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c";
const OPTION_NAME_LABEL = "\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435";
const OPTION_START_LABEL = "\u041d\u0430\u0447\u0430\u043b\u043e";
const OPTION_END_LABEL = "\u041a\u043e\u043d\u0435\u0446";

export interface PollOptionDraft {
  label: string;
  start_at: string;
  end_at: string;
}

interface PollOptionFieldsProps {
  options: PollOptionDraft[];
  onAddOption: () => void;
  onUpdateOption: (index: number, field: keyof PollOptionDraft, value: string) => void;
}

export function PollOptionFields({ options, onAddOption, onUpdateOption }: PollOptionFieldsProps) {
  return (
    <section className="options-section">
      <div className="participant-section__header">
        <h2>{OPTIONS_TITLE}:</h2>
        <button className="text-link" type="button" onClick={onAddOption}>
          {ADD_OPTION_LABEL}
        </button>
      </div>

      <div className="options-list">
        {options.map((option, index) => (
          <article className="option-card" key={index}>
            <label className="field-stack">
              <span>{OPTION_NAME_LABEL}</span>
              <input
                value={option.label}
                onChange={(event) => onUpdateOption(index, "label", event.target.value)}
                required
              />
            </label>
            <label className="field-stack">
              <span>{OPTION_START_LABEL}</span>
              <input
                type="datetime-local"
                value={option.start_at}
                onChange={(event) => onUpdateOption(index, "start_at", event.target.value)}
                required
              />
            </label>
            <label className="field-stack">
              <span>{OPTION_END_LABEL}</span>
              <input
                type="datetime-local"
                value={option.end_at}
                onChange={(event) => onUpdateOption(index, "end_at", event.target.value)}
                required
              />
            </label>
          </article>
        ))}
      </div>
    </section>
  );
}
