import { create } from "zustand";
import { persist } from "zustand/middleware";

export type VisitorType = "adult" | "small_child" | "child" | "teen";

export interface PartyEntry {
  type: VisitorType;
  count: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface SessionState {
  sessionId: string | null;
  visitDate: string | null;
  party: PartyEntry[];
  jwt: string | null;
  messages: ChatMessage[];

  setVisitDate: (date: string) => void;
  setPartyCount: (type: VisitorType, count: number) => void;
  setSessionId: (id: string) => void;
  setJwt: (token: string) => void;
  addMessage: (msg: ChatMessage) => void;
  reset: () => void;
}

const DEFAULT_PARTY: PartyEntry[] = [
  { type: "adult", count: 0 },
  { type: "small_child", count: 0 },
  { type: "child", count: 0 },
  { type: "teen", count: 0 },
];

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      sessionId: null,
      visitDate: null,
      party: DEFAULT_PARTY,
      jwt: null,
      messages: [],

      setVisitDate: (date) => set({ visitDate: date }),

      setPartyCount: (type, count) =>
        set((s) => ({
          party: s.party.map((p) => (p.type === type ? { ...p, count: Math.max(0, count) } : p)),
        })),

      setSessionId: (id) => set({ sessionId: id }),
      setJwt: (token) => set({ jwt: token }),
      addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

      reset: () =>
        set({ sessionId: null, visitDate: null, party: DEFAULT_PARTY, jwt: null, messages: [] }),
    }),
    { name: "plume-session" }
  )
);
