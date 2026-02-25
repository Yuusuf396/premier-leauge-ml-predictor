import React from 'react';
import { BackendBanner } from './components/BackendBanner';
import { ErrorAlert } from './components/ErrorAlert';
import { Header } from './components/Header';
import { MatchContextRow } from './components/MatchContextRow';
import { PredictButton } from './components/PredictButton';
import { PredictionResultCard } from './components/PredictionResultCard';
import { SkeletonCard } from './components/SkeletonCard';
import { TeamSelector } from './components/TeamSelector';
import { VSDivider } from './components/VSDivider';
import { useAppState } from './hooks/useAppState';
import { useReducedMotion } from './hooks/useReducedMotion';

export default function App() {
  const { state, dispatch, handleGenerate } = useAppState();
  const prefersReducedMotion = useReducedMotion();

  return (
    <div className="min-h-screen bg-[#0c0f29] font-[Inter,sans-serif] text-white">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        @keyframes shimmer { to { transform: translateX(200%) } }
        @keyframes shake { 0%,100% { transform: translateX(0) } 50% { transform: translateX(5px) } }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #121845; }
        ::-webkit-scrollbar-thumb { background: #1e2a6e; border-radius: 2px; }
      `}</style>

      <Header />

      <main className="mx-auto max-w-[420px] px-4 pb-24 pt-10">
        {state.backendUp === false && <BackendBanner />}

        {state.status === 'boot' ? (
          <div className="flex flex-col items-center justify-center gap-4 py-20">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#097aff] border-t-transparent" />
            <p className="text-sm text-[#8891B8]">Connecting...</p>
          </div>
        ) : (
          <>
            <h1 className="mb-1 text-2xl font-bold tracking-tight">
              Match Predictor
            </h1>
            <p className="mb-8 text-sm text-[#8891B8]">
              Select two teams to generate an analytical prediction.
            </p>

            <div className="mb-5 rounded-2xl border border-[#1e2a6e] bg-[#121845] p-5">
              <div className="grid grid-cols-[1fr_40px_1fr] items-start gap-2">
                <TeamSelector
                  side="Home"
                  selectedTeam={state.homeTeam}
                  otherTeam={state.awayTeam}
                  teams={state.teams}
                  onSelect={(team) => dispatch({ type: 'SELECT_HOME', team })}
                  onClear={() => dispatch({ type: 'CLEAR_HOME' })}
                />
                <VSDivider />
                <TeamSelector
                  side="Away"
                  selectedTeam={state.awayTeam}
                  otherTeam={state.homeTeam}
                  teams={state.teams}
                  onSelect={(team) => dispatch({ type: 'SELECT_AWAY', team })}
                  onClear={() => dispatch({ type: 'CLEAR_AWAY' })}
                />
              </div>
            </div>

            {state.homeTeam && state.awayTeam && (
              <MatchContextRow homeTeam={state.homeTeam} awayTeam={state.awayTeam} />
            )}

            <div className="mb-8 mt-5">
              <PredictButton
                status={state.status}
                backendUp={state.backendUp}
                onGenerate={handleGenerate}
              />
            </div>

            {state.status === 'loading' && <SkeletonCard />}

            {state.status === 'result' && state.prediction && state.homeTeam && state.awayTeam && (
              <PredictionResultCard
                prediction={state.prediction}
                homeTeam={state.homeTeam}
                awayTeam={state.awayTeam}
                prefersReducedMotion={prefersReducedMotion}
                onReset={() => dispatch({ type: 'RESET' })}
              />
            )}

            {state.status === 'error' && state.error && (
              <ErrorAlert
                message={state.error.message}
                onRetry={() => dispatch({ type: 'RESET' })}
              />
            )}
          </>
        )}
      </main>
    </div>
  );
}
