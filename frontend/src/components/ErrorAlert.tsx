import { AlertCircle } from 'lucide-react';
import { useEffect, useState } from 'react';

interface ErrorAlertProps {
  message: string;
  onRetry: () => void;
}

export function ErrorAlert({ message, onRetry }: ErrorAlertProps) {
  const [shaking, setShaking] = useState(false);

  useEffect(() => {
    setShaking(true);
    const timer = window.setTimeout(() => setShaking(false), 400);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <div
      className={`rounded-2xl border border-[#1e2a6e] border-l-4 border-l-[#FF3B5C] bg-[#121845] p-4 ${
        shaking ? 'animate-[shake_0.15s_ease-in-out_2]' : ''
      }`}
    >
      <div className="flex items-start gap-3">
        <AlertCircle
          size={20}
          className="mt-0.5 shrink-0 text-[#FF3B5C]"
        />
        <div className="min-w-0">
          <p className="mb-1 text-sm font-bold text-white">
            Unable to generate prediction
          </p>
          <p className="text-xs leading-relaxed text-[#8891B8]">{message}</p>
        </div>
      </div>
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 rounded-lg border border-[#097aff]/40 px-4 py-1.5 text-xs font-semibold text-[#097aff] transition-colors hover:bg-[#097aff]/10"
      >
        Try again
      </button>
    </div>
  );
}
