import { useEffect, useState } from "react";
import { bootstrapSession, getCurrentSession } from "../api";
import { initTelegramApp } from "../telegram";
import type { SessionPayload } from "../types";

export function useSessionState() {
  const [token, setToken] = useState<string>(() => localStorage.getItem("scheduler.token") ?? "");
  const [session, setSession] = useState<SessionPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      return;
    }

    let active = true;
    async function refreshSession() {
      try {
        const current = await getCurrentSession(token);
        if (!active) {
          return;
        }
        setSession({ access_token: token, user: current.user, workspaces: current.workspaces });
        setError(null);
      } catch (requestError) {
        if (active) {
          setError(requestError instanceof Error ? requestError.message : "Unable to refresh session");
        }
      }
    }

    function handleVisibilityChange() {
      if (document.visibilityState === "visible") {
        void refreshSession();
      }
    }

    function handleFocus() {
      void refreshSession();
    }

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("focus", handleFocus);

    return () => {
      active = false;
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("focus", handleFocus);
    };
  }, [token]);

  useEffect(() => {
    let active = true;
    async function bootstrapWithInitData(initData: string) {
      const payload = await bootstrapSession(initData);
      if (!active) {
        return;
      }
      localStorage.setItem("scheduler.token", payload.access_token);
      setToken(payload.access_token);
      setSession(payload);
      setError(null);
    }

    (async () => {
      try {
        const hasTelegramWebApp = Boolean(window.Telegram?.WebApp);
        const initData = await initTelegramApp();
        if (initData) {
          if (!token) {
            await bootstrapWithInitData(initData);
            return;
          }

          try {
            const current = await getCurrentSession(token);
            if (!active) {
              return;
            }
            setSession({ access_token: token, user: current.user, workspaces: current.workspaces });
            setError(null);
            return;
          } catch {
            await bootstrapWithInitData(initData);
          }
          return;
        }

        if (hasTelegramWebApp) {
          localStorage.removeItem("scheduler.token");
          if (!active) {
            return;
          }
          setToken("");
          setSession(null);
          throw new Error("Telegram session not found. Reopen the Mini App from the bot menu.");
        }

        if (!token) {
          const payload = await bootstrapSession("");
          if (!active) {
            return;
          }
          localStorage.setItem("scheduler.token", payload.access_token);
          setToken(payload.access_token);
          setSession(payload);
          return;
        }

        const current = await getCurrentSession(token);
        if (!active) {
          return;
        }
        setSession({ access_token: token, user: current.user, workspaces: current.workspaces });
      } catch (requestError) {
        if (active) {
          setError(requestError instanceof Error ? requestError.message : "Unable to bootstrap session");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    })();

    return () => {
      active = false;
    };
  }, [token]);

  return { token, session, loading, error };
}
