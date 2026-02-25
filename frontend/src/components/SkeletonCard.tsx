function Shimmer({ className }: { className: string }) {
  return (
    <div className={`relative overflow-hidden rounded-lg bg-[#1a2260] ${className}`}>
      <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.5s_infinite] bg-gradient-to-r from-transparent via-[#2a3580]/50 to-transparent" />
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div>
      <div className="rounded-2xl border border-[#1e2a6e] bg-[#121845] p-6">
        <div className="flex items-center justify-between gap-3">
          <Shimmer className="h-4 w-24" />
          <Shimmer className="h-3 w-6" />
          <Shimmer className="h-4 w-24" />
        </div>

        <div className="my-4 border-t border-[#1e2a6e]" />

        <div className="grid grid-cols-3 items-end text-center">
          <div className="flex justify-center">
            <Shimmer className="h-10 w-16" />
          </div>
          <div className="flex justify-center">
            <Shimmer className="h-3 w-8" />
          </div>
          <div className="flex justify-center">
            <Shimmer className="h-10 w-16" />
          </div>
        </div>

        <div className="mt-5 space-y-3">
          <Shimmer className="h-2.5 w-full rounded-full" />
          <Shimmer className="h-2.5 w-full rounded-full" />
          <Shimmer className="h-2.5 w-full rounded-full" />
        </div>

        <div className="mt-5 flex justify-center">
          <Shimmer className="h-8 w-48 rounded-full" />
        </div>

        <div className="mt-5 border-t border-[#1e2a6e] pt-4">
          <div className="flex justify-center">
            <Shimmer className="h-3 w-64" />
          </div>
        </div>
      </div>

      <p className="mt-6 text-center text-xs text-[#8891B8] animate-pulse">
        Analysing match data...
      </p>
    </div>
  );
}
