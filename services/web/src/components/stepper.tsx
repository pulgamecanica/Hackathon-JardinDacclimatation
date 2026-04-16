"use client";

interface StepperProps {
  label: string;
  sublabel?: string;
  value: number;
  onChange: (v: number) => void;
}

export default function Stepper({ label, sublabel, value, onChange }: StepperProps) {
  return (
    <div
      className="flex items-center justify-between rounded-[16px] px-4 bg-white h-[67px]"
      style={{ border: "2px solid #2D6A4F26" }}
    >
      <div className="text-[14px] leading-[20px] text-[#374151] whitespace-nowrap">
        {label}
        {sublabel && <span className="text-[#9CA3AF] ml-1">({sublabel})</span>}
      </div>
      <div className="flex items-center gap-[18px]">
        <button
          type="button"
          onClick={() => onChange(value - 1)}
          disabled={value <= 0}
          className="w-[26px] h-[26px] rounded-full flex items-center justify-center text-sm leading-none hover:opacity-80 disabled:opacity-30 disabled:cursor-not-allowed transition-colors cursor-pointer"
          style={{ backgroundColor: "#EFF3EE", color: "#6B7280" }}
        >
          &minus;
        </button>
        <span
          className="w-5 text-center text-[24px] leading-[32px] text-[#374151]"
          style={{ fontFamily: "var(--font-cormorant), serif", fontWeight: 400 }}
        >
          {value}
        </span>
        <button
          type="button"
          onClick={() => onChange(value + 1)}
          className="w-[26px] h-[26px] rounded-full flex items-center justify-center text-sm leading-none hover:opacity-80 transition-colors cursor-pointer"
          style={{ backgroundColor: "#EFF3EE", color: "#6B7280" }}
        >
          +
        </button>
      </div>
    </div>
  );
}
