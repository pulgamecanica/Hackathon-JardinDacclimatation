const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001";

export interface TicketResponse {
  id: string;
  date: string;
  visitor_type: string;
  status: string;
  purchased: boolean;
  locked: boolean;
  payment_reference?: string;
  purchased_at?: string;
}

export interface ChatMessageResponse {
  id: string;
  role: string;
  content: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface SessionResponse {
  id: string;
  status: string;
  visit_date: string;
  party: { type: string; count: number }[];
  party_size: number;
  preferences: Record<string, unknown>;
  has_tickets: boolean;
  tickets: TicketResponse[];
  group_id: string | null;
  user_id: string | null;
  created_at: string;
  updated_at: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  createSession(body: { visit_date: string; party: { type: string; count: number }[] }) {
    return request<SessionResponse>("/api/v1/sessions", {
      method: "POST",
      body: JSON.stringify({ session: body }),
    });
  },

  getSession(id: string) {
    return request<SessionResponse>(`/api/v1/sessions/${id}`);
  },

  updateSession(id: string, body: Partial<{ visit_date: string; party: { type: string; count: number }[]; preferences: Record<string, unknown> }>) {
    return request<SessionResponse>(`/api/v1/sessions/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ session: body }),
    });
  },

  linkTicket(sessionId: string, code: string, visitorType = "adult") {
    return request<{ session: SessionResponse; ticket: TicketResponse }>(
      `/api/v1/sessions/${sessionId}/link_ticket`,
      {
        method: "POST",
        body: JSON.stringify({ code, visitor_type: visitorType }),
      }
    );
  },

  linkGroup(sessionId: string, code: string) {
    return request<SessionResponse>(`/api/v1/sessions/${sessionId}/link_group`, {
      method: "POST",
      body: JSON.stringify({ code }),
    });
  },

  getTickets(sessionId: string) {
    return request<TicketResponse[]>(`/api/v1/sessions/${sessionId}/tickets`);
  },

  getChatMessages(sessionId: string, after?: string) {
    const qs = after ? `?after=${encodeURIComponent(after)}` : "";
    return request<ChatMessageResponse[]>(
      `/api/v1/sessions/${sessionId}/chat_messages${qs}`
    );
  },

  /**
   * Send a chat message. Rails persists it, dispatches to the AI
   * orchestrator via Celery, and returns immediately. The frontend
   * polls getChatMessages(?after=id) for the assistant reply.
   */
  sendChatMessage(sessionId: string, message: string) {
    return request<{ chat_message: ChatMessageResponse; status: string }>(
      `/api/v1/sessions/${sessionId}/chat`,
      {
        method: "POST",
        body: JSON.stringify({ message }),
      }
    );
  },

  requestMagicLink(email: string) {
    return fetch(`${API_URL}/api/v1/auth/request_link`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
  },

  verifyMagicLink(token: string) {
    return request<{ token: string; user: { id: string; email: string } }>(
      "/api/v1/auth/verify",
      {
        method: "POST",
        body: JSON.stringify({ token }),
      }
    );
  },
};
