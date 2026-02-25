interface ProbabilityBarProps {
  label: string;
  value: number;
  color: string;
  isDominant: boolean;
  delay: number;
  animated: boolean;
}

export function ProbabilityBar({
  label,
  value,
  color,
  isDominant,
  delay,
  animated,
}: ProbabilityBarProps) {
  return (
    <div className="flex items-center gap-3">
      <span
        className={`w-16 shrink-0 text-xs ${
          isDominant
            ? 'font-bold text-white'
            : 'font-medium text-[#8891B8]'
        }`}
      >
        {label}
      </span>
      <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-[#1e2a6e]">
        <div
          className="h-full rounded-full transition-[width] ease-out"
          style={{
            width: animated ? `${value}%` : '0%',
            backgroundColor: color,
            opacity: isDominant ? 1 : 0.6,
            transitionDuration: '800ms',
            transitionDelay: `${delay}ms`,
          }}
        />
      </div>
      <span
        className={`w-9 shrink-0 text-right text-xs tabular-nums ${
          isDominant ? 'font-bold text-white' : 'text-[#8891B8]'
        }`}
      >
        {value}%
      </span>
    </div>
  );
}
