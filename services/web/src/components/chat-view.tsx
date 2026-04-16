"use client";

import { useEffect, useRef, useState } from "react";
import { useSessionStore } from "@/store/session";

const AI_URL = process.env.NEXT_PUBLIC_AI_URL ?? "http://localhost:8000";

export default function ChatView() {
  const { sessionId, messages, addMessage, party, visitDate } = useSessionStore();
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    const text = input.trim();
    if (!text || !sessionId || streaming) return;
    setInput("");
    addMessage({ role: "user", content: text });
    setStreaming(true);

    let assistantText = "";
    try {
      const res = await fetch(`${AI_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message: text,
          visit_date: visitDate,
          party,
        }),
      });

      if (!res.ok || !res.body) throw new Error("stream failed");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          try {
            const evt = JSON.parse(line.slice(6));
            if (evt.type === "token" && evt.text) {
              assistantText += evt.text;
            }
          } catch {
            /* ignore malformed SSE lines */
          }
        }
      }
    } catch {
      assistantText = assistantText || "Désolé, une erreur est survenue.";
    }

    addMessage({ role: "assistant", content: assistantText });
    setStreaming(false);
  }

  const totalVisitors = party.reduce((s, p) => s + p.count, 0);

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      <div className="border-b border-gray-100 px-6 py-3 text-sm text-gray-500 flex gap-4">
        {visitDate && <span>Date : {visitDate}</span>}
        <span>Visiteurs : {totalVisitors}</span>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <p className="text-center text-gray-400 mt-12">
            Bonjour ! Posez-moi vos questions sur votre visite.
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`max-w-xl ${m.role === "user" ? "ml-auto" : "mr-auto"}`}
          >
            <div
              className={`rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap ${
                m.role === "user"
                  ? "bg-teal text-white rounded-br-sm"
                  : "bg-gray-100 text-gray-800 rounded-bl-sm"
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}
        {streaming && (
          <div className="mr-auto">
            <div className="bg-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 text-sm text-gray-400 animate-pulse">
              ...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={(e) => { e.preventDefault(); send(); }}
        className="border-t border-gray-100 px-6 py-3 flex gap-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Votre message..."
          className="flex-1 border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-teal"
          disabled={streaming}
        />
        <button
          type="submit"
          disabled={!input.trim() || streaming}
          className="bg-teal text-white rounded-xl px-5 py-2.5 text-sm font-medium hover:bg-teal-dark disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          Envoyer
        </button>
      </form>
    </div>
  );
}
