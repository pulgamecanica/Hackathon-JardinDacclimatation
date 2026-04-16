const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001";
const AI_URL = process.env.NEXT_PUBLIC_AI_URL ?? "http://localhost:8000";

async function request<T>(base: string, path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  createSession(body: { visit_date: string; party: { type: string; count: number }[] }) {
    return request<{ id: string }>(API_URL, "/api/v1/sessions", {
      method: "POST",
      body: JSON.stringify({ session: body }),
    });
  },

  getSession(id: string) {
    return request<Record<string, unknown>>(API_URL, `/api/v1/sessions/${id}`);
  },

  requestMagicLink(email: string) {
    return fetch(`${API_URL}/api/v1/auth/request_link`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
  },

  verifyMagicLink(token: string) {
    return request<{ token: string }>(API_URL, "/api/v1/auth/verify", {
      method: "POST",
      body: JSON.stringify({ token }),
    });
  },

  chatStream(sessionId: string, message: string): EventSource | ReadableStream {
    const url = `${AI_URL}/chat?session_id=${encodeURIComponent(sessionId)}&message=${encodeURIComponent(message)}`;
    return new EventSource(url);
  },
};
