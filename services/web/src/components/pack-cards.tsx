"use client";

import { useState } from "react";
import type { PackOffer } from "@/lib/api";
import { api } from "@/lib/api";
import { useSessionStore } from "@/store/session";

interface Props {
  packs: PackOffer[];
  disabled?: boolean;
}

export default function PackCards({ packs, disabled }: Props) {
  const { sessionId, setTickets, setPreferences, preferences } = useSessionStore();
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ ok: boolean; msg: string } | null>(null);

  const selectedPackId =
    typeof preferences?.selected_pack === "object" && preferences.selected_pack !== null
      ? (preferences.selected_pack as { id?: string }).id ?? null
      : null;

  async function handleSelect(pack: PackOffer) {
    if (!sessionId || pendingId) return;
    setPendingId(pack.id);
    setFeedback(null);
    try {
      const res = await api.selectPack(sessionId, pack);
      setTickets(res.session.tickets);
      setPreferences(res.session.preferences ?? {});
      setFeedback({ ok: true, msg: `${pack.name} — ${res.created_ticket_ids.length} billet(s) simulé(s) créé(s).` });
    } catch {
      setFeedback({ ok: false, msg: "Impossible d'ajouter ce pack. Merci de réessayer." });
    }
    setPendingId(null);
  }

  if (packs.length === 0) return null;

  return (
    <div className="mt-3 space-y-3">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {packs.map((pack) => {
          const isSelected = selectedPackId === pack.id;
          const isPending = pendingId === pack.id;
          return (
            <article
              key={pack.id}
              className={`rounded-2xl border p-4 flex flex-col gap-3 transition-colors ${
                pack.recommended
                  ? "border-teal bg-teal-light/30"
                  : "border-gray-200 bg-white"
              }`}
            >
              <header className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="text-sm font-medium text-gray-900">{pack.name}</h3>
                  <p className="text-xs text-gray-500 mt-0.5">{pack.description}</p>
                </div>
                {pack.recommended && (
                  <span className="shrink-0 text-[10px] uppercase tracking-wide text-teal font-semibold bg-teal/10 px-2 py-0.5 rounded-full">
                    Recommandé
                  </span>
                )}
              </header>

              {pack.highlight_features.length > 0 && (
                <ul className="text-xs text-gray-600 space-y-1">
                  {pack.highlight_features.map((feature, fi) => (
                    <li key={fi} className="flex items-start gap-1.5">
                      <span className="text-teal mt-0.5">•</span>
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              )}

              <div className="mt-auto pt-2 border-t border-gray-100 flex items-center justify-between">
                <span className="text-lg font-medium text-gray-900">
                  {pack.total_eur.toFixed(2).replace(".", ",")}&nbsp;€
                </span>
                <button
                  type="button"
                  onClick={() => handleSelect(pack)}
                  disabled={disabled || isPending || isSelected}
                  className={`text-xs px-3 py-1.5 rounded-full font-medium transition-colors ${
                    isSelected
                      ? "bg-teal/10 text-teal cursor-default"
                      : "bg-teal text-white hover:bg-teal-dark disabled:opacity-40 disabled:cursor-not-allowed"
                  }`}
                >
                  {isSelected ? "Sélectionné" : isPending ? "..." : "Sélectionner"}
                </button>
              </div>
            </article>
          );
        })}
      </div>

      {feedback && (
        <p
          className={`text-xs ml-1 ${
            feedback.ok ? "text-teal" : "text-red-400"
          }`}
        >
          {feedback.msg}
        </p>
      )}
    </div>
  );
}
