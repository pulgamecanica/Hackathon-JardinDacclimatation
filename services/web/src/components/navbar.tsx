import Link from "next/link";

const NAV_LINKS = [
  { label: "Le Jardin", href: "#" },
  { label: "Ateliers", href: "#" },
  { label: "Attractions", href: "#" },
  { label: "Animations", href: "#" },
  { label: "Restaurants", href: "#" },
  { label: "Tarifs", href: "#" },
  { label: "Votre visite", href: "#" },
];

export default function Navbar() {
  return (
    <header
      className="fixed top-0 left-0 w-full z-50 flex items-center justify-between h-[70px] px-10 overflow-visible"
      style={{ backgroundColor: "#212F2D", color: "#FCFCFC" }}
    >
      {/* Left nav links */}
      <nav className="flex gap-5 text-sm text-white/80">
        {NAV_LINKS.map((l) => (
          <Link
            key={l.label}
            href={l.href}
            className="hover:text-white transition-colors whitespace-nowrap"
          >
            {l.label}
          </Link>
        ))}
      </nav>

      {/* Center logo — positioned to overflow below the navbar */}
      <Link
        href="/"
        className="absolute left-1/2 -translate-x-1/2 top-0 z-[51] h-[70px] flex items-center"
      >
        <div className="w-[72px] h-[72px] rounded-full bg-white border-[1.5px] border-[#212F2D] flex items-center justify-center shadow-sm translate-y-[16px]">
          <div className="text-center text-[#212F2D]">
            <span
              className="text-[8px] leading-[9px] block italic"
              style={{ fontFamily: "var(--font-cormorant), serif" }}
            >
              le Jardin
            </span>
            <span
              className="text-[7px] leading-[8px] block italic"
              style={{ fontFamily: "var(--font-cormorant), serif" }}
            >
              d&apos;Acclimatation
            </span>
            <span className="text-[4.5px] tracking-[1.5px] uppercase block mt-0.5">
              Paris — 1860
            </span>
          </div>
        </div>
      </Link>

      {/* Right actions */}
      <div className="flex items-center gap-2.5">
        {/* Account icon */}
        <button className="hidden sm:flex w-9 h-9 rounded-sm border border-white/30 items-center justify-center text-white hover:border-[#07E0C0] hover:text-[#07E0C0] transition-colors">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
          </svg>
        </button>

        {/* BILLETTERIE + Cart joined */}
        <div className="flex rounded-[4px] overflow-hidden" style={{ backgroundColor: "#07E0C0", boxShadow: "0px 3px 5px 1px rgba(48,48,48,0.2)" }}>
          {/* BILLETTERIE button */}
          <Link
            href="#"
            className="flex items-center gap-3 h-9 px-3 text-[14px] uppercase tracking-[-0.28px]"
            style={{ color: "#212F2D" }}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 6v.75m0 3v.75m0 3v.75m0 3V18m-9-5.25h5.25M7.5 15h3M3.375 5.25c-.621 0-1.125.504-1.125 1.125v3.026a2.999 2.999 0 0 1 0 5.198v3.026c0 .621.504 1.125 1.125 1.125h17.25c.621 0 1.125-.504 1.125-1.125v-3.026a2.999 2.999 0 0 1 0-5.198V6.375c0-.621-.504-1.125-1.125-1.125H3.375Z" />
            </svg>
            Billetterie
          </Link>

          {/* Cart button — inset 1px top/bottom so teal peeks through */}
          <button
            className="flex items-center gap-2.5 px-2.5"
            style={{ backgroundColor: "#212F2D", color: "#FCFCFC", margin: "1px 1px 1px 0", borderRadius: "0 3px 3px 0" }}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 10.5V6a3.75 3.75 0 1 0-7.5 0v4.5m11.356-1.993 1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 0 1-1.12-1.243l1.264-12A1.125 1.125 0 0 1 5.513 7.5h12.974c.576 0 1.059.435 1.119 1.007ZM8.625 10.5a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm7.5 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" />
            </svg>
            <span aria-hidden="true">0</span>
          </button>
        </div>
      </div>
    </header>
  );
}
