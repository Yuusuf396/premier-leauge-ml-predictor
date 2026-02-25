import { Zap } from 'lucide-react';
import type { AppStatus } from '../hooks/useAppState';

interface PredictButtonProps {
  status: AppStatus;
  backendUp: boolean | null;
  onGenerate: () => void;
}

export function PredictButton({
  status,
  backendUp,
  onGenerate,
}: PredictButtonProps) {
  const disabled = status !== 'ready' || backendUp === false;

  const variantClass =
    status === 'loading'
      ? 'bg-[#097aff] pointer-events-none text-white'
      : disabled
        ? 'bg-[#1e2a6e] text-[#4a5280] cursor-not-allowed opacity-60'
        : 'bg-[#097aff] text-white cursor-pointer shadow-[0_8px_20px_rgba(9,122,255,0.4)] hover:scale-[1.02] active:scale-[0.97]';

  return (
    <button
      type="button"
      onClick={onGenerate}
      disabled={disabled || status === 'loading'}
      className={`flex h-14 w-full items-center justify-center gap-2 rounded-full text-base font-semibold transition-all duration-200 ${variantClass}`}
    >
      {status === 'loading' ? (
        <>
          <svg
            className="h-5 w-5 animate-spin text-white"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v8z"
            />
          </svg>
          Analysing Fixture...
        </>
      ) : (
        <>
          <Zap size={18} />
          Generate Prediction
        </>
      )}
    </button>
  );
}
