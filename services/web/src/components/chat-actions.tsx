"use client";

import { useState } from "react";
import { useSessionStore } from "@/store/session";
import { api } from "@/lib/api";

export default function ChatActions() {
  const { sessionId, setTickets, setGroup } = useSessionStore();
  const [open, setOpen] = useState<"ticket" | "group" | null>(null);
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ ok: boolean; msg: string } | null>(null);

  if (!sessionId) return null;

  function clearState() {
    setCode("");
    setFeedback(null);
    setLoading(false);
  }

  async function handleLinkTicket() {
    if (!code.trim() || !sessionId) return;
    setLoading(true);
    setFeedback(null);
    try {
      const res = await api.linkTicket(sessionId, code.trim());
      setTickets(res.session.tickets);
      setFeedback({ ok: true, msg: "Billet li\u00e9 avec succ\u00e8s !" });
      setCode("");
    } catch {
      setFeedback({ ok: false, msg: "Code invalide ou erreur serveur." });
    }
    setLoading(false);
  }

  async function handleLinkGroup() {
    if (!code.trim() || !sessionId) return;
    setLoading(true);
    setFeedback(null);
    try {
      const res = await api.linkGroup(sessionId, code.trim());
      setGroup(res.group_id ?? "", code.trim());
      setFeedback({ ok: true, msg: "Groupe li\u00e9 avec succ\u00e8s !" });
      setCode("");
    } catch {
      setFeedback({ ok: false, msg: "Code de groupe invalide." });
    }
    setLoading(false);
  }

  function toggle(panel: "ticket" | "group") {
    if (open === panel) {
      setOpen(null);
      clearState();
    } else {
      setOpen(panel);
      clearState();
    }
  }

  return (
    <div className="border-b border-gray-100">
      {/* Action buttons */}
      <div className="px-6 py-2 flex gap-2">
        <button
          type="button"
          onClick={() => toggle("ticket")}
          className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
            open === "ticket"
              ? "border-teal bg-teal-light text-teal"
              : "border-gray-200 text-gray-500 hover:border-gray-300"
          }`}
        >
          <svg className="w-3.5 h-3.5 inline-block mr-1 -mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 6v.75m0 3v.75m0 3v.75m0 3V18m-9-5.25h5.25M7.5 15h3M3.375 5.25c-.621 0-1.125.504-1.125 1.125v3.026a2.999 2.999 0 0 1 0 5.198v3.026c0 .621.504 1.125 1.125 1.125h17.25c.621 0 1.125-.504 1.125-1.125v-3.026a2.999 2.999 0 0 1 0-5.198V6.375c0-.621-.504-1.125-1.125-1.125H3.375Z" />
          </svg>
          Lier un billet
        </button>
        <button
          type="button"
          onClick={() => toggle("group")}
          className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
            open === "group"
              ? "border-teal bg-teal-light text-teal"
              : "border-gray-200 text-gray-500 hover:border-gray-300"
          }`}
        >
          <svg className="w-3.5 h-3.5 inline-block mr-1 -mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z" />
          </svg>
          Rejoindre un groupe
        </button>
      </div>

      {/* Expandable panel */}
      {open && (
        <div className="px-6 pb-3">
          <div className="flex gap-2">
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder={open === "ticket" ? "Code du billet..." : "Code du groupe..."}
              className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-teal"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  open === "ticket" ? handleLinkTicket() : handleLinkGroup();
                }
              }}
            />
            <button
              type="button"
              disabled={!code.trim() || loading}
              onClick={open === "ticket" ? handleLinkTicket : handleLinkGroup}
              className="bg-teal text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-teal-dark disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? "..." : "Lier"}
            </button>
          </div>
          {feedback && (
            <p className={`text-xs mt-1.5 ml-1 ${feedback.ok ? "text-teal" : "text-red-400"}`}>
              {feedback.msg}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
