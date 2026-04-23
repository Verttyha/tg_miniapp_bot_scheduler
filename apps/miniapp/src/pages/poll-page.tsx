import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getPoll, resolvePoll, voteOnPoll } from "../api";
import { ScreenHeader } from "../components/layout/screen-header";
import { countPollVotes, formatDateTime, translatePollStatus } from "../lib/formatters";
import { isWorkspaceAdmin } from "../lib/workspace";
import type { Poll, SessionPayload } from "../types";

const POLL_PAGE_TEXT = {
  loadError: "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0433\u043e\u043b\u043e\u0441\u043e\u0432\u0430\u043d\u0438\u0435",
  voteError: "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u0433\u043e\u043b\u043e\u0441",
  resolveError: "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u044c \u0433\u043e\u043b\u043e\u0441\u043e\u0432\u0430\u043d\u0438\u0435",
  eyebrow: "\u0413\u043e\u043b\u043e\u0441\u043e\u0432\u0430\u043d\u0438\u0435",
  loadingTitle: "\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u0433\u043e\u043b\u043e\u0441\u043e\u0432\u0430\u043d\u0438\u044f",
  loadingOptions: "\u041f\u043e\u0434\u0433\u0440\u0443\u0436\u0430\u044e \u0432\u0430\u0440\u0438\u0430\u043d\u0442\u044b...",
  deadline: "\u0414\u0435\u0434\u043b\u0430\u0439\u043d",
  voted: "\u043f\u0440\u043e\u0433\u043e\u043b\u043e\u0441\u043e\u0432\u0430\u043b\u0438",
  chatOnly:
    "\u0413\u043e\u043b\u043e\u0441\u043e\u0432\u0430\u043d\u0438\u0435 \u0438\u0434\u0435\u0442 \u0432 Telegram-\u0447\u0430\u0442\u0435. \u0411\u043e\u0442 \u0441\u0430\u043c \u0441\u0447\u0438\u0442\u0430\u0435\u0442 \u043e\u0442\u0432\u0435\u0442\u044b \u0438 \u0437\u0430\u043a\u0440\u043e\u0435\u0442 poll \u0432 \u043c\u043e\u043c\u0435\u043d\u0442 \u0434\u0435\u0434\u043b\u0430\u0439\u043d\u0430.",
  optionPrefix: "\u0412\u0430\u0440\u0438\u0430\u043d\u0442",
  votes: "\u0433\u043e\u043b\u043e\u0441\u043e\u0432",
  resolveButton:
    "\u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u044c \u0433\u043e\u043b\u043e\u0441\u043e\u0432\u0430\u043d\u0438\u0435 \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u044b\u043c \u0432\u0430\u0440\u0438\u0430\u043d\u0442\u043e\u043c",
  adminResolveOnly:
    "\u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u044c \u0433\u043e\u043b\u043e\u0441\u043e\u0432\u0430\u043d\u0438\u0435 \u043c\u043e\u0436\u0435\u0442 \u0442\u043e\u043b\u044c\u043a\u043e \u0430\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440 \u0447\u0430\u0442\u0430."
};

export function PollPage({ token, session }: { token: string; session: SessionPayload }) {
  const { pollId } = useParams();
  const [poll, setPoll] = useState<Poll | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!pollId) {
      return;
    }
    let active = true;
    (async () => {
      try {
        const data = await getPoll(Number(pollId), token);
        if (active) {
          setPoll(data);
          setError(null);
        }
      } catch (requestError) {
        if (active) {
          setError(requestError instanceof Error ? requestError.message : POLL_PAGE_TEXT.loadError);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [pollId, token]);

  async function handleVote(optionId: number) {
    if (!poll) {
      return;
    }
    try {
      setPoll(await voteOnPoll(poll.id, optionId, token));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : POLL_PAGE_TEXT.voteError);
    }
  }

  async function handleResolve() {
    if (!poll) {
      return;
    }
    try {
      setPoll(await resolvePoll(poll.id, poll.user_vote_option_id, token));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : POLL_PAGE_TEXT.resolveError);
    }
  }

  const workspace = poll
    ? session.workspaces.find((item) => item.id === poll.workspace_id) ?? session.workspaces[0] ?? null
    : session.workspaces[0] ?? null;
  const canManageWorkspace = workspace ? isWorkspaceAdmin(workspace, session.user.id) : false;
  const voteInChatOnly = Boolean(poll?.has_chat_poll && poll.status === "open");

  return (
    <section className="detail-screen">
      <ScreenHeader
        backTo={workspace ? `/workspaces/${workspace.id}` : "/"}
        eyebrow={POLL_PAGE_TEXT.eyebrow}
        title={poll?.title ?? POLL_PAGE_TEXT.loadingTitle}
        description={poll ? `\u0421\u0442\u0430\u0442\u0443\u0441: ${translatePollStatus(poll.status)}` : undefined}
      />

      {error ? <div className="notice notice--error">{error}</div> : null}

      {!poll ? (
        <div className="empty-card">{POLL_PAGE_TEXT.loadingOptions}</div>
      ) : (
        <>
          <div className="status-banner">
            {POLL_PAGE_TEXT.deadline}: {formatDateTime(poll.deadline_at)} | {POLL_PAGE_TEXT.voted} {countPollVotes(poll)}
          </div>
          {voteInChatOnly ? (
            <div className="status-banner status-banner--muted">{POLL_PAGE_TEXT.chatOnly}</div>
          ) : null}
          <div className="vote-list">
            {poll.options.map((option) => {
              const selected = poll.user_vote_option_id === option.id;
              const className = `vote-card ${selected ? "vote-card--selected" : ""} ${voteInChatOnly ? "vote-card--readonly" : ""}`.trim();

              if (voteInChatOnly) {
                return (
                  <article className={className} key={option.id}>
                    <strong>{option.label ?? `${POLL_PAGE_TEXT.optionPrefix} ${option.id}`}</strong>
                    <span>{formatDateTime(option.start_at)}</span>
                    <span>{option.vote_count} {POLL_PAGE_TEXT.votes}</span>
                  </article>
                );
              }

              return (
                <button className={className} key={option.id} type="button" onClick={() => handleVote(option.id)}>
                  <strong>{option.label ?? `${POLL_PAGE_TEXT.optionPrefix} ${option.id}`}</strong>
                  <span>{formatDateTime(option.start_at)}</span>
                  <span>{option.vote_count} {POLL_PAGE_TEXT.votes}</span>
                </button>
              );
            })}
          </div>
          {poll.status === "needs_admin_resolution" ? (
            canManageWorkspace ? (
              <button className="action-pill action-pill--full" type="button" onClick={handleResolve}>
                {POLL_PAGE_TEXT.resolveButton}
              </button>
            ) : (
              <div className="status-banner status-banner--muted">{POLL_PAGE_TEXT.adminResolveOnly}</div>
            )
          ) : null}
        </>
      )}
    </section>
  );
}
