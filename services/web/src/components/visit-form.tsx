"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useSessionStore, type VisitorType } from "@/store/session";
import { useHydrated } from "@/lib/use-hydrated";
import { api } from "@/lib/api";
import Calendar from "./calendar";
import Stepper from "./stepper";
import StepDots from "./step-dots";
import Pavo, { type PavoState } from "./pavo";

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

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export default function VisitForm() {
  const router = useRouter();
  const hydrated = useHydrated();
  const {
    visitDate, party, email, sessionId,
    setVisitDate, setPartyCount, setEmail, setSessionId,
    setTickets, setPreferences,
  } = useSessionStore();
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [emailTouched, setEmailTouched] = useState(false);

  const totalVisitors = party.reduce((sum, p) => sum + p.count, 0);
  const emailValid = email !== null && isValidEmail(email);
  const canContinue = hydrated && visitDate !== null && totalVisitors > 0 && emailValid;
  const hasExistingSession = hydrated && sessionId !== null;

  const pavoState: PavoState = calendarOpen
    ? "calendar"
    : canContinue
    ? "notes"
    : "normal";

  // Loading skeleton
  if (!hydrated) {
    return (
      <div className="w-full min-h-screen bg-gradient-to-b from-gray-50 to-white px-4 py-6 sm:py-8">
        <div className="max-w-[672px] mx-auto">
          <div className="h-2 w-24 bg-gray-200 rounded-full mx-auto mb-8 animate-pulse" />
          <div className="text-center mb-8 sm:mb-12">
            <div className="h-12 sm:h-16 bg-gray-200 rounded-lg max-w-[300px] mx-auto mb-3 animate-pulse" />
            <div className="h-6 bg-gray-200 rounded w-48 mx-auto animate-pulse" />
          </div>
          <div className="bg-white rounded-2xl p-4 sm:p-6 lg:p-8 h-[400px] animate-pulse shadow-sm" />
        </div>
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
      setTickets(res.tickets ?? []);
      setPreferences(res.preferences ?? {});
      if (email) {
        api.requestMagicLink(email).catch(() => {});
      }
      router.push("/chat");
    } catch {
      setLoading(false);
    }
  }

  function handleResumeSession() {
    router.push("/chat");
  }

  return (
    <div className="w-full min-h-screen bg-gradient-to-b from-gray-50/80 to-white px-4 py-6 sm:py-8 lg:py-12">
      <div className="max-w-[672px] mx-auto">
        {/* Progress Indicator - Mobile optimized */}
        <div className="mb-6 sm:mb-8">
          <StepDots total={3} current={0} />
        </div>

        {/* Resume Session Banner - Touch friendly */}
        {hasExistingSession && (
          <div className="border border-teal/20 rounded-2xl px-4 sm:px-6 py-4 mb-4 sm:mb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-[0_2px_8px_rgba(0,0,0,0.04)] bg-white/50 backdrop-blur-sm">
            <div className="flex-1 min-w-0">
              <p className="text-sm sm:text-base font-semibold text-[#1A1A1A]">Vous avez une visite en cours</p>
              <p className="text-xs sm:text-sm text-[#6B7280] mt-1 truncate">
                {visitDate ? formatDateFr(visitDate) : ""}
                {totalVisitors > 0 ? ` · ${totalVisitors} visiteur${totalVisitors > 1 ? "s" : ""}` : ""}
              </p>
            </div>
            <button
              type="button"
              onClick={handleResumeSession}
              className="w-full sm:w-auto bg-teal text-white rounded-xl px-5 py-3 sm:py-2.5 text-sm font-semibold hover:bg-teal-dark active:scale-95 transition-all min-h-[44px] touch-manipulation"
            >
              Reprendre
            </button>
          </div>
        )}

        {/* Main Form Card — relative wrapper anchors Pavo above & behind */}
        <div className="relative mt-[160px]">
          <Pavo state={pavoState} />
        <div className="relative z-10 bg-white rounded-2xl sm:rounded-3xl px-4 sm:px-6 lg:px-10 py-6 sm:py-8 space-y-6 sm:space-y-8 shadow-[0_4px_20px_rgba(0,0,0,0.06)] border border-gray-100">
          
          {/* Email Section */}
          <section className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-semibold text-[#374151] mb-2">
              <svg className="w-5 h-5 text-[#6B7280] flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
              </svg>
              <span className="text-[clamp(0.875rem,3vw,0.9375rem)]">Votre email</span>
            </label>
            <div className="relative">
              <input
                type="email"
                inputMode="email"
                autoComplete="email"
                value={email ?? ""}
                onChange={(e) => setEmail(e.target.value)}
                onBlur={() => setEmailTouched(true)}
                placeholder="prenom@exemple.fr"
                className={`w-full border-2 rounded-xl px-4 py-4 bg-white text-base sm:text-sm transition-all duration-200 focus:outline-none focus:ring-4 focus:ring-teal/10 min-h-[56px] touch-manipulation ${
                  emailTouched && !emailValid
                    ? "border-red-300 focus:border-red-400 focus:ring-red-100"
                    : "border-gray-200 hover:border-gray-300 focus:border-teal"
                }`}
              />
            </div>
            {emailTouched && !emailValid && (
              <p className="text-xs sm:text-sm text-red-500 mt-2 ml-1 font-medium animate-in slide-in-from-top-1">
                Veuillez entrer un email valide
              </p>
            )}
          </section>

          {/* Date Section */}
          <section className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-semibold text-[#374151] mb-2">
              <svg className="w-5 h-5 text-[#6B7280] flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" />
              </svg>
              <span className="text-[clamp(0.875rem,3vw,0.9375rem)]">Date de visite</span>
            </label>

            <button
              type="button"
              onClick={() => setCalendarOpen(!calendarOpen)}
              className="w-full text-left border-2 border-gray-200 rounded-xl px-4 py-4 bg-white text-base sm:text-sm hover:border-gray-300 active:border-teal transition-all duration-200 min-h-[56px] touch-manipulation flex items-center justify-between group"
            >
              {visitDate ? (
                <span className="capitalize text-[#1A1A1A] font-medium">{formatDateFr(visitDate)}</span>
              ) : (
                <span className="text-gray-400">Sélectionner une date</span>
              )}
              <svg 
                className={`w-5 h-5 text-gray-400 transition-transform duration-200 ${calendarOpen ? 'rotate-180' : ''}`} 
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {calendarOpen && (
              <div className="mt-3 animate-in fade-in slide-in-from-top-2 duration-200">
                <Calendar
                  selected={visitDate}
                  onSelect={(d) => { setVisitDate(d); setCalendarOpen(false); }}
                />
              </div>
            )}
          </section>

          {/* Visitors Section - Mobile optimized grid */}
          <section className="space-y-3">
            <label className="flex items-center gap-2 text-sm font-semibold text-[#374151] mb-3">
              <svg className="w-5 h-5 text-[#6B7280] flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z" />
              </svg>
              <span className="text-[clamp(0.875rem,3vw,0.9375rem)]">Nombre de Visiteurs</span>
            </label>

            {/* Single column on mobile, 2 columns on sm+ */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
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

          {/* Continue Button - Thumb friendly, sticky on mobile */}
          <div className="pt-2 sm:pt-4">
            <button
              type="button"
              disabled={!canContinue || loading}
              onClick={handleContinue}
              className={`
                w-full rounded-2xl text-base sm:text-sm font-semibold transition-all duration-200 
                min-h-[56px] sm:h-[68px] touch-manipulation active:scale-[0.98]
                flex items-center justify-center gap-2
                ${canContinue
                  ? "bg-teal text-white hover:bg-teal-dark hover:shadow-lg hover:shadow-teal/25"
                  : "bg-gray-200 text-gray-400 cursor-not-allowed"
                }
              `}
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Chargement...
                </>
              ) : (
                "Discuter avec Pavo"
              )}
            </button>
          </div>
        </div>
        </div>

        {hasExistingSession && (
          <p className="text-center text-xs sm:text-sm text-gray-400 mt-4 sm:mt-6 px-4">
            ou créez une nouvelle visite ci-dessus
          </p>
        )}
      </div>
    </div>
  );
}