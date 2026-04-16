interface StepDotsProps {
  total: number;
  current: number;
}

export default function StepDots({ total, current }: StepDotsProps) {
  return (
    <div className="flex items-center justify-center pt-2 pb-8">
      <div
        className="flex items-center gap-3 rounded-full px-6 py-3"
        style={{
          background: "#FFFFFFE5",
          border: "1px solid #06D6B726",
          boxShadow: "0px 4px 6px -4px #0000001A, 0px 10px 15px -3px #0000001A",
        }}
      >
        {Array.from({ length: total }, (_, i) => (
          <div
            key={i}
            className={`h-[6px] rounded-full transition-all ${
              i === current ? "w-[18px]" : "w-[6px]"
            }`}
            style={{ backgroundColor: i === current ? "#015425" : "#D1D5DC" }}
          />
        ))}
      </div>
    </div>
  );
}
