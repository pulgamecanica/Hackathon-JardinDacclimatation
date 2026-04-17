"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSessionStore } from "@/store/session";
import { api } from "@/lib/api";

const POLL_INTERVAL_MS = 1500;
const MAX_POLLS = 120; // give up after ~3 minutes

function extractSuggestions(meta: Record<string, unknown> | undefined): string[] | undefined {
  const raw = meta?.suggestions;
  if (!Array.isArray(raw)) return undefined;
  const items = raw.filter((s): s is string => typeof s === "string" && s.trim().length > 0);
  return items.length > 0 ? items : undefined;
}

export default function ChatView() {
  const {
    sessionId, messages, addMessage,
    party, visitDate, tickets, groupId,
  } = useSessionStore();
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load persisted chat history from the server on mount
  useEffect(() => {
    if (!sessionId || historyLoaded) return;
    api.getChatMessages(sessionId).then((serverMsgs) => {
      if (messages.length === 0 && serverMsgs.length > 0) {
        for (const m of serverMsgs) {
          addMessage({
            role: m.role as "user" | "assistant",
            content: m.content,
            suggestions: extractSuggestions(m.metadata),
          });
        }
      }
      setHistoryLoaded(true);
    }).catch(() => setHistoryLoaded(true));
  }, [sessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, thinking]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearTimeout(pollRef.current);
    };
  }, []);

  const pollForReply = useCallback((afterId: string, attempt = 0) => {
    if (!sessionId || attempt >= MAX_POLLS) {
      setThinking(false);
      if (attempt >= MAX_POLLS) {
        addMessage({ role: "assistant", content: "D\u00e9sol\u00e9, la r\u00e9ponse a pris trop de temps. Veuillez r\u00e9essayer." });
      }
      return;
    }

    pollRef.current = setTimeout(async () => {
      try {
        const newMsgs = await api.getChatMessages(sessionId, afterId);
        const assistantMsg = newMsgs.find((m) => m.role === "assistant");
        if (assistantMsg) {
          addMessage({
            role: "assistant",
            content: assistantMsg.content,
            suggestions: extractSuggestions(assistantMsg.metadata),
          });
          setThinking(false);
          return;
        }
      } catch {
        // Network blip — keep polling
      }
      pollForReply(afterId, attempt + 1);
    }, POLL_INTERVAL_MS);
  }, [sessionId, addMessage]);

  const sendText = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || !sessionId || thinking) return;
    addMessage({ role: "user", content: trimmed });
    setThinking(true);

    try {
      const res = await api.sendChatMessage(sessionId, trimmed);
      pollForReply(res.chat_message.id);
    } catch {
      addMessage({ role: "assistant", content: "D\u00e9sol\u00e9, une erreur est survenue." });
      setThinking(false);
    }
  }, [sessionId, thinking, addMessage, pollForReply]);

  async function send() {
    const text = input.trim();
    if (!text) return;
    setInput("");
    await sendText(text);
  }

  // Poll for the proactive greeting on first chat-view mount when there
  // are no messages yet — orchestrator-driven welcome lands in metadata.
  useEffect(() => {
    if (!sessionId || !historyLoaded || messages.length > 0 || thinking) return;
    setThinking(true);
    pollForReply("");
  }, [sessionId, historyLoaded, messages.length, thinking, pollForReply]);

  // Show chips only on the latest assistant message (avoid clutter).
  const lastAssistantIdx = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") return i;
    }
    return -1;
  })();

  const totalVisitors = party.reduce((s, p) => s + p.count, 0);
  const ticketCount = tickets.length;

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      {/* Context bar */}
      <div className="border-b border-gray-100 px-6 py-3 text-sm text-gray-500 flex items-center gap-4">
        {visitDate && <span>Date : {visitDate}</span>}
        <span>Visiteurs : {totalVisitors}</span>
        {ticketCount > 0 && (
          <span className={tickets.some((t) => t.purchased) ? "text-teal" : ""}>
            Billets : {ticketCount}
            {tickets.some((t) => t.purchased) && " (achet\u00e9s)"}
          </span>
        )}
        {groupId && (
          <span className="text-teal">Groupe li\u00e9</span>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && !thinking && (
          <div className="text-center mt-12 space-y-2">
            <p className="text-2xl" style={{ fontFamily: "var(--font-cormorant), serif" }}>
              Bonjour, je suis <span className="text-teal font-medium">Pavo</span>
            </p>
            <p className="text-gray-400 text-sm max-w-md mx-auto">
              Votre assistant pour planifier votre visite au Jardin d&apos;Acclimatation.
              Posez-moi vos questions sur les attractions, le parcours, les horaires&hellip;
            </p>
          </div>
        )}
        {messages.map((m, i) => {
          const showChips =
            m.role === "assistant" &&
            i === lastAssistantIdx &&
            !thinking &&
            (m.suggestions?.length ?? 0) > 0;
          return (
            <div
              key={i}
              className={`max-w-xl ${m.role === "user" ? "ml-auto" : "mr-auto"}`}
            >
              {m.role === "assistant" && (
                <span className="text-xs text-teal font-medium ml-1 mb-1 block">Pavo</span>
              )}
              <div
                className={`rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap ${
                  m.role === "user"
                    ? "bg-teal text-white rounded-br-sm"
                    : "bg-gray-100 text-gray-800 rounded-bl-sm"
                }`}
              >
                {m.content}
              </div>
              {showChips && (
                <div className="flex flex-wrap gap-2 mt-2 ml-1">
                  {m.suggestions!.map((chip, ci) => (
                    <button
                      key={ci}
                      type="button"
                      onClick={() => sendText(chip)}
                      disabled={thinking}
                      className="text-xs px-3 py-1.5 rounded-full border border-teal/30 bg-teal/5 text-teal hover:bg-teal hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      {chip}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}

        {/* Pavo thinking indicator */}
        {thinking && (
          <div className="mr-auto max-w-xl">
            <span className="text-xs text-teal font-medium ml-1 mb-1 block">Pavo</span>
            <div className="bg-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 inline-flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-teal/60 animate-bounce [animation-delay:0ms]" />
              <span className="w-2 h-2 rounded-full bg-teal/60 animate-bounce [animation-delay:150ms]" />
              <span className="w-2 h-2 rounded-full bg-teal/60 animate-bounce [animation-delay:300ms]" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={(e) => { e.preventDefault(); send(); }}
        className="border-t border-gray-100 px-6 py-3 flex gap-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Votre message..."
          className="flex-1 border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-teal"
          disabled={thinking}
        />
        <button
          type="submit"
          disabled={!input.trim() || thinking}
          className="bg-teal text-white rounded-xl px-5 py-2.5 text-sm font-medium hover:bg-teal-dark disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          Envoyer
        </button>
      </form>
    </div>
  );
}
