import { FormEvent, useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { createPoll } from "../api";
import { ParticipantSelector } from "../components/forms/participant-selector";
import { PollOptionFields, type PollOptionDraft } from "../components/forms/poll-option-fields";
import { ScreenHeader } from "../components/layout/screen-header";
import { LineField } from "../components/ui/line-field";
import { isWorkspaceAdmin } from "../lib/workspace";
import type { SessionPayload } from "../types";

const POLL_EDITOR_TEXT = {
  eyebrow: "\u0413\u043e\u043b\u043e\u0441\u043e\u0432\u0430\u043d\u0438\u0435",
  createTitle: "\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u043e\u043f\u0440\u043e\u0441",
  description:
    "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043d\u0435\u0441\u043a\u043e\u043b\u044c\u043a\u043e \u0432\u0430\u0440\u0438\u0430\u043d\u0442\u043e\u0432 \u0432\u0440\u0435\u043c\u0435\u043d\u0438, \u0430 \u043a\u043e\u043c\u0430\u043d\u0434\u0430 \u043f\u0440\u043e\u0433\u043e\u043b\u043e\u0441\u0443\u0435\u0442",
  adminOnly: "\u0421\u043e\u0437\u0434\u0430\u0432\u0430\u0442\u044c \u043e\u043f\u0440\u043e\u0441\u044b \u043c\u043e\u0433\u0443\u0442 \u0442\u043e\u043b\u044c\u043a\u043e \u0430\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440\u044b \u0447\u0430\u0442\u0430.",
  createError: "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0441\u043e\u0437\u0434\u0430\u0442\u044c \u0433\u043e\u043b\u043e\u0441\u043e\u0432\u0430\u043d\u0438\u0435",
  titleLabel: "\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435",
  deadlineLabel: "\u0414\u0435\u0434\u043b\u0430\u0439\u043d",
  descriptionLabel: "\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435",
  descriptionPlaceholder:
    "\u0427\u0442\u043e \u0443\u0447\u0430\u0441\u0442\u043d\u0438\u043a\u0430\u043c \u0432\u0430\u0436\u043d\u043e \u0437\u043d\u0430\u0442\u044c \u043f\u0435\u0440\u0435\u0434 \u0433\u043e\u043b\u043e\u0441\u043e\u0432\u0430\u043d\u0438\u0435\u043c",
  createButton: "\u0421\u043e\u0437\u0434\u0430\u0442\u044c",
  cancelButton: "\u041e\u0442\u043c\u0435\u043d\u0430",
  optionPrefix: "\u0412\u0430\u0440\u0438\u0430\u043d\u0442"
};

const INITIAL_OPTIONS: PollOptionDraft[] = [
  { label: `${POLL_EDITOR_TEXT.optionPrefix} 1`, start_at: "", end_at: "" },
  { label: `${POLL_EDITOR_TEXT.optionPrefix} 2`, start_at: "", end_at: "" }
];

export function PollEditorPage({ token, session }: { token: string; session: SessionPayload }) {
  const { workspaceId } = useParams();
  const navigate = useNavigate();
  const workspace = session.workspaces.find((item) => item.id === Number(workspaceId));
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [deadlineAt, setDeadlineAt] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>(workspace?.members.map((member) => member.user.id) ?? []);
  const [options, setOptions] = useState<PollOptionDraft[]>(INITIAL_OPTIONS);
  const [error, setError] = useState<string | null>(null);

  if (!workspace) {
    return <Navigate to="/" replace />;
  }

  const canManageWorkspace = isWorkspaceAdmin(workspace, session.user.id);

  if (!canManageWorkspace) {
    return (
      <section className="editor-screen">
        <ScreenHeader
          backTo={`/workspaces/${workspace.id}`}
          eyebrow={POLL_EDITOR_TEXT.eyebrow}
          title={POLL_EDITOR_TEXT.createTitle}
          description={POLL_EDITOR_TEXT.description}
        />
        <div className="notice">{POLL_EDITOR_TEXT.adminOnly}</div>
      </section>
    );
  }

  function toggleParticipant(userId: number) {
    setSelectedIds((current) => (current.includes(userId) ? current.filter((id) => id !== userId) : [...current, userId]));
  }

  function addOption() {
    setOptions((current) => [...current, { label: `${POLL_EDITOR_TEXT.optionPrefix} ${current.length + 1}`, start_at: "", end_at: "" }]);
  }

  function updateOption(index: number, field: keyof PollOptionDraft, value: string) {
    setOptions((current) =>
      current.map((item, currentIndex) => (currentIndex === index ? { ...item, [field]: value } : item))
    );
  }

  async function handleSubmit(submitEvent: FormEvent<HTMLFormElement>) {
    submitEvent.preventDefault();
    try {
      await createPoll(
        workspace.id,
        {
          title,
          description,
          deadline_at: new Date(deadlineAt).toISOString(),
          timezone_name: Intl.DateTimeFormat().resolvedOptions().timeZone,
          participant_ids: selectedIds,
          options: options.map((option) => ({
            label: option.label,
            start_at: new Date(option.start_at).toISOString(),
            end_at: new Date(option.end_at).toISOString()
          }))
        },
        token
      );
      navigate(`/workspaces/${workspace.id}`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : POLL_EDITOR_TEXT.createError);
    }
  }

  return (
    <section className="editor-screen">
      <ScreenHeader
        backTo={`/workspaces/${workspace.id}`}
        eyebrow={POLL_EDITOR_TEXT.eyebrow}
        title={POLL_EDITOR_TEXT.createTitle}
        description={POLL_EDITOR_TEXT.description}
      />

      {error ? <div className="notice notice--error">{error}</div> : null}

      <form className="editor-form" onSubmit={handleSubmit}>
        <LineField label={POLL_EDITOR_TEXT.titleLabel}>
          <input value={title} onChange={(event) => setTitle(event.target.value)} required />
        </LineField>

        <LineField label={POLL_EDITOR_TEXT.deadlineLabel}>
          <input
            type="datetime-local"
            value={deadlineAt}
            onChange={(event) => setDeadlineAt(event.target.value)}
            required
          />
        </LineField>

        <LineField label={POLL_EDITOR_TEXT.descriptionLabel} multiline>
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={3}
            placeholder={POLL_EDITOR_TEXT.descriptionPlaceholder}
          />
        </LineField>

        <ParticipantSelector members={workspace.members} onToggle={toggleParticipant} selectedIds={selectedIds} />

        <PollOptionFields onAddOption={addOption} onUpdateOption={updateOption} options={options} />

        <div className="editor-actions">
          <button className="action-pill" type="submit">
            {POLL_EDITOR_TEXT.createButton}
          </button>
          <button className="action-pill action-pill--ghost" type="button" onClick={() => navigate(`/workspaces/${workspace.id}`)}>
            {POLL_EDITOR_TEXT.cancelButton}
          </button>
        </div>
      </form>
    </section>
  );
}
