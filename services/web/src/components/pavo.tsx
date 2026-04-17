"use client";

import Image from "next/image";

export type PavoState = "normal" | "calendar" | "notes" | "approves" | "paying";

type Variant = {
  src: string;
  width: number;
  height: number;
  displayWidth: number;
  overlap: number;
};

const VARIANTS: Record<PavoState, Variant> = {
  normal:   { src: "/pavo/normal.webp",   width: 1090, height: 855, displayWidth: 240, overlap: 70 },
  calendar: { src: "/pavo/calendar.webp", width: 1151, height: 855, displayWidth: 280, overlap: 60 },
  notes:    { src: "/pavo/notes.webp",    width: 1355, height: 711, displayWidth: 320, overlap: 26 },
  approves: { src: "/pavo/approves.webp", width: 839,  height: 855, displayWidth: 220, overlap: 70 },
  paying:   { src: "/pavo/paying.webp",   width: 1127, height: 643, displayWidth: 300, overlap: 40 },
};

const ORDER: PavoState[] = ["normal", "calendar", "notes", "approves", "paying"];

export default function Pavo({ state }: { state: PavoState }) {
  return (
    <>
      {ORDER.map((key) => {
        const v = VARIANTS[key];
        const h = Math.round((v.displayWidth * v.height) / v.width);
        const active = key === state;
        return (
          <Image
            key={key}
            src={v.src}
            alt=""
            aria-hidden="true"
            width={v.width}
            height={v.height}
            priority={key === "normal"}
            draggable={false}
            className="pointer-events-none select-none absolute transition-opacity duration-300 ease-out"
            style={{
              width: `${v.displayWidth}px`,
              height: `${h}px`,
              left: "50%",
              bottom: `calc(100% - ${v.overlap}px)`,
              transform: "translateX(-50%)",
              opacity: active ? 1 : 0,
              zIndex: 0,
            }}
          />
        );
      })}
    </>
  );
}
