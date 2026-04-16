"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useSessionStore, type VisitorType } from "@/store/session";
import { useHydrated } from "@/lib/use-hydrated";
import { api } from "@/lib/api";
import Calendar from "./calendar";
import Stepper from "./stepper";
import StepDots from "./step-dots";

const VISITOR_CONFIG: { type: VisitorType; label: string; sublabel?: string }[] = [
  { type: "adult", label: "Adultes" },
  { type: "small_child", label: "Petits", sublabel: "3-7 ans" },
  { type: "child", label: "Enfants", sublabel: "8-12 ans" },
  { type: "teen", label: "Ados", sublabel: "13-16 ans" },
];

function formatDateFr(iso: string): string {
  const d = new Date(iso + "T12:00:00");
  return d.toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
}

export default function VisitForm() {
  const router = useRouter();
  const hydrated = useHydrated();
  const { visitDate, party, setVisitDate, setPartyCount, setSessionId } = useSessionStore();
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const totalVisitors = party.reduce((sum, p) => sum + p.count, 0);
  const canContinue = hydrated && visitDate !== null && totalVisitors > 0;

  if (!hydrated) {
    return (
      <div className="w-full max-w-[672px] mx-auto px-4">
        <StepDots total={3} current={0} />
        <div className="text-center mb-12">
          <h1
            className="whitespace-nowrap text-[60px] leading-[60px] font-medium mb-2 text-[#1A1A1A]"
            style={{ fontFamily: "var(--font-cormorant), serif" }}
          >
            Jardin d&apos;Acclimatation
          </h1>
          <p className="text-[18px] leading-[28px] text-teal">
            Planifiez votre visite
          </p>
        </div>
        <div className="bg-white rounded-2xl p-8 h-[420px] animate-pulse shadow-[0_4px_20px_rgba(0,0,0,0.06)]" />
      </div>
    );
  }

  async function handleContinue() {
    if (!canContinue || !visitDate) return;
    setLoading(true);
    try {
      const activeParty = party.filter((p) => p.count > 0);
      const res = await api.createSession({ visit_date: visitDate, party: activeParty });
      setSessionId(res.id);
      router.push("/chat");
    } catch {
      setLoading(false);
    }
  }

  return (
    <div className="w-full max-w-[672px] mx-auto px-4">
      <StepDots total={3} current={0} />

      <div className="text-center mb-12">
        <h1
          className="whitespace-nowrap text-[60px] leading-[60px] font-medium mb-2 text-[#1A1A1A]"
          style={{ fontFamily: "var(--font-cormorant), serif" }}
        >
          Jardin d&apos;Acclimatation
        </h1>
        <p className="text-[18px] leading-[28px] text-teal">
          Planifiez votre visite
        </p>
      </div>

      <div className="bg-white rounded-2xl px-10 py-8 space-y-6 shadow-[0_4px_20px_rgba(0,0,0,0.06)]">
        {/* Date de visite */}
        <section>
          <label className="flex items-center gap-2 text-[13px] font-medium text-[#374151] mb-2.5">
            <svg className="w-[16px] h-[16px] text-[#6B7280]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" />
            </svg>
            Date de visite
          </label>

          <button
            type="button"
            onClick={() => setCalendarOpen(!calendarOpen)}
            className="w-full text-left border border-[#E5E7EB] rounded-xl px-4 py-4 bg-white text-[14px] hover:border-[#D1D5DB] transition-colors"
          >
            {visitDate ? (
              <span className="capitalize text-[#1A1A1A]">{formatDateFr(visitDate)}</span>
            ) : (
              <span className="text-[#9CA3AF]">S&eacute;lectionner une date</span>
            )}
          </button>

          {calendarOpen && (
            <div className="mt-3">
              <Calendar
                selected={visitDate}
                onSelect={(d) => { setVisitDate(d); setCalendarOpen(false); }}
              />
            </div>
          )}
        </section>

        {/* Nombre de Visiteurs */}
        <section>
          <label className="flex items-center gap-2 text-[13px] font-medium text-[#374151] mb-2.5">
            <svg className="w-[16px] h-[16px] text-[#6B7280]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z" />
            </svg>
            Nombre de Visiteurs
          </label>

          <div className="grid grid-cols-2 gap-3">
            {VISITOR_CONFIG.map((v) => {
              const entry = party.find((p) => p.type === v.type);
              return (
                <Stepper
                  key={v.type}
                  label={v.label}
                  sublabel={v.sublabel}
                  value={entry?.count ?? 0}
                  onChange={(n) => setPartyCount(v.type, n)}
                />
              );
            })}
          </div>
        </section>

        {/* Continue button */}
        <button
          type="button"
          disabled={!canContinue || loading}
          onClick={handleContinue}
          className={`
            w-full h-[68px] rounded-[16px] text-[14px] font-medium transition-all
            ${canContinue
              ? "bg-teal text-white hover:bg-teal-dark cursor-pointer"
              : "cursor-not-allowed"
            }
          `}
          style={canContinue ? {} : {
            backgroundColor: "#E5E7EB",
            color: "#9CA3AF",
            boxShadow: "0px 4px 6px -4px #0000001A, 0px 10px 15px -3px #0000001A",
          }}
        >
          {loading ? "Chargement..." : "Continue"}
        </button>
      </div>
    </div>
  );
}
