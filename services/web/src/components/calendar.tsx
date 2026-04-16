"use client";

import { useState, useMemo } from "react";

const DAYS_FR = ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"];
const MONTHS_FR = [
  "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
];

interface CalendarProps {
  selected: string | null;
  onSelect: (iso: string) => void;
}

export default function Calendar({ selected, onSelect }: CalendarProps) {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const cells = useMemo(() => {
    const arr: (number | null)[] = Array(firstDay).fill(null);
    for (let d = 1; d <= daysInMonth; d++) arr.push(d);
    return arr;
  }, [firstDay, daysInMonth]);

  function iso(day: number) {
    return `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  }

  function isPast(day: number) {
    const d = new Date(year, month, day);
    const t = new Date();
    t.setHours(0, 0, 0, 0);
    return d < t;
  }

  function isToday(day: number) {
    const t = new Date();
    return year === t.getFullYear() && month === t.getMonth() && day === t.getDate();
  }

  function prev() {
    if (month === 0) { setMonth(11); setYear(year - 1); }
    else setMonth(month - 1);
  }

  function next() {
    if (month === 11) { setMonth(0); setYear(year + 1); }
    else setMonth(month + 1);
  }

  return (
    <div className="border border-[#E5E7EB] rounded-xl p-5 bg-[#F9FAFB]">
      {/* Month header */}
      <div className="flex items-center justify-between mb-4">
        <button type="button" onClick={prev} className="text-[#9CA3AF] hover:text-teal px-2 transition-colors">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
          </svg>
        </button>
        <span
          className="text-base font-medium text-[#1A1A1A]"
          style={{ fontFamily: "var(--font-cormorant), serif" }}
        >
          {MONTHS_FR[month]} {year}
        </span>
        <button type="button" onClick={next} className="text-[#9CA3AF] hover:text-teal px-2 transition-colors">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
          </svg>
        </button>
      </div>

      {/* Day headers */}
      <div className="grid grid-cols-7 text-center text-xs text-[#9CA3AF] mb-2">
        {DAYS_FR.map((d) => <div key={d} className="py-1">{d}</div>)}
      </div>

      {/* Day cells */}
      <div className="grid grid-cols-7 gap-1 text-center text-sm">
        {cells.map((day, i) =>
          day === null ? (
            <div key={`e${i}`} />
          ) : (
            <button
              key={day}
              type="button"
              disabled={isPast(day)}
              onClick={() => onSelect(iso(day))}
              className={`
                w-10 h-10 mx-auto rounded-full flex items-center justify-center transition-colors text-sm
                ${isPast(day) ? "text-[#D1D5DB] cursor-not-allowed" : "hover:bg-teal-light cursor-pointer"}
                ${selected === iso(day) ? "bg-teal text-white font-medium" : ""}
                ${isToday(day) && selected !== iso(day) ? "border border-teal text-teal" : ""}
              `}
            >
              {day}
            </button>
          )
        )}
      </div>

      {/* Affluence legend */}
      <div className="flex items-center gap-2 mt-4 text-xs text-[#9CA3AF]">
        <span>Affluence :</span>
        <span className="w-2.5 h-2.5 rounded-full bg-[#34D399]" />
        <span className="w-2.5 h-2.5 rounded-full bg-[#FBBF24]" />
        <span className="w-2.5 h-2.5 rounded-full bg-[#F87171]" />
      </div>
    </div>
  );
}
