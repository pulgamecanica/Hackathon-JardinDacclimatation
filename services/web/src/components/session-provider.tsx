"use client";

import { useEffect, useRef } from "react";
import { useSessionStore } from "@/store/session";

/**
 * Runs once on mount: if zustand has a persisted sessionId,
 * validates it against the API and rehydrates full session data
 * (tickets, group, preferences). If the session is gone (404),
 * resets the store so the user starts fresh.
 */
export default function SessionProvider({ children }: { children: React.ReactNode }) {
  const rehydrateFromApi = useSessionStore((s) => s.rehydrateFromApi);
  const sessionId = useSessionStore((s) => s.sessionId);
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;
    if (sessionId) {
      rehydrateFromApi();
    }
  }, [sessionId, rehydrateFromApi]);

  return <>{children}</>;
}
