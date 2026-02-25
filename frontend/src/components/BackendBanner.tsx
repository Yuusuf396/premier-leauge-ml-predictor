import { WifiOff } from 'lucide-react';

export function BackendBanner() {
  return (
    <div className="mb-6 flex items-center gap-3 rounded-xl border border-[#FF3B5C]/30 bg-[#FF3B5C]/10 px-4 py-3">
      <WifiOff size={16} className="shrink-0 text-[#FF3B5C]" />
      <p className="text-xs text-[#FF3B5C]">
        Backend unavailable — running in offline mode. Predictions disabled.
      </p>
    </div>
  );
}
