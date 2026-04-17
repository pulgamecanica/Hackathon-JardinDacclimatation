import { create } from "zustand";
import { persist } from "zustand/middleware";
import { api, type PackOffer, type SessionResponse, type TicketResponse } from "@/lib/api";

export type VisitorType = "adult" | "small_child" | "child" | "teen";

export interface PartyEntry {
  type: VisitorType;
  count: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  suggestions?: string[];
  packs?: PackOffer[];
}

interface SessionState {
  sessionId: string | null;
  visitDate: string | null;
  party: PartyEntry[];
  email: string | null;
  jwt: string | null;
  messages: ChatMessage[];
  tickets: TicketResponse[];
  groupId: string | null;
  groupCode: string | null;
  preferences: Record<string, unknown>;
  status: string | null;

  setVisitDate: (date: string) => void;
  setPartyCount: (type: VisitorType, count: number) => void;
  setSessionId: (id: string) => void;
  setEmail: (email: string) => void;
  setJwt: (token: string) => void;
  addMessage: (msg: ChatMessage) => void;
  setTickets: (tickets: TicketResponse[]) => void;
  setGroup: (groupId: string, groupCode: string) => void;
  setPreferences: (prefs: Record<string, unknown>) => void;
  rehydrateFromApi: () => Promise<boolean>;
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
    (set, get) => ({
      sessionId: null,
      visitDate: null,
      party: DEFAULT_PARTY,
      email: null,
      jwt: null,
      messages: [],
      tickets: [],
      groupId: null,
      groupCode: null,
      preferences: {},
      status: null,

      setVisitDate: (date) => set({ visitDate: date }),

      setPartyCount: (type, count) =>
        set((s) => ({
          party: s.party.map((p) => (p.type === type ? { ...p, count: Math.max(0, count) } : p)),
        })),

      setSessionId: (id) => set({ sessionId: id }),
      setEmail: (email) => set({ email }),
      setJwt: (token) => set({ jwt: token }),
      addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
      setTickets: (tickets) => set({ tickets }),
      setGroup: (groupId, groupCode) => set({ groupId, groupCode }),
      setPreferences: (prefs) => set({ preferences: prefs }),

      rehydrateFromApi: async () => {
        const { sessionId } = get();
        if (!sessionId) return false;
        try {
          const data = await api.getSession(sessionId);
          set({
            visitDate: data.visit_date,
            party: (data.party as PartyEntry[]) ?? DEFAULT_PARTY,
            tickets: data.tickets ?? [],
            groupId: data.group_id ?? null,
            preferences: data.preferences ?? {},
            status: data.status,
          });
          return true;
        } catch {
          // Session no longer exists on the server — reset
          set({
            sessionId: null,
            visitDate: null,
            party: DEFAULT_PARTY,
            messages: [],
            tickets: [],
            groupId: null,
            groupCode: null,
            preferences: {},
            status: null,
          });
          return false;
        }
      },

      reset: () =>
        set({
          sessionId: null,
          visitDate: null,
          party: DEFAULT_PARTY,
          email: null,
          jwt: null,
          messages: [],
          tickets: [],
          groupId: null,
          groupCode: null,
          preferences: {},
          status: null,
        }),
    }),
    { name: "pavo-session" }
  )
);
