import { useEffect, useState } from 'react';
import { useCounter } from '../hooks/useCounter';
import { ProbabilityBar } from './ProbabilityBar';
import type {
  NormalisedProbs,
  Outcome,
  PredictionResponse,
  Team,
} from '../types/api';

interface PredictionResultCardProps {
  prediction: PredictionResponse;
  homeTeam: Team;
  awayTeam: Team;
  prefersReducedMotion: boolean;
  onReset: () => void;
}

function normaliseProbs(
  home: number,
  draw: number,
  away: number,
): NormalisedProbs {
  let homeWin = Math.round(home * 100);
  let drawPct = Math.round(draw * 100);
  let awayWin = 100 - homeWin - drawPct;

  if (awayWin < 0) {
    if (homeWin >= drawPct) {
      homeWin = Math.max(0, homeWin + awayWin);
    } else {
      drawPct = Math.max(0, drawPct + awayWin);
    }
    awayWin = 0;
  }

  return { homeWin, draw: drawPct, awayWin };
}

const BADGE_STYLES: Record<Outcome, string> = {
  home: 'bg-[#00D68F]/20 text-[#00D68F] border-[#00D68F]/30',
  draw: 'bg-[#F5A623]/20 text-[#F5A623] border-[#F5A623]/30',
  away: 'bg-[#097aff]/20 text-[#097aff] border-[#097aff]/30',
};

export function PredictionResultCard({
  prediction,
  homeTeam,
  awayTeam,
  prefersReducedMotion,
  onReset,
}: PredictionResultCardProps) {
  const [visible, setVisible] = useState(false);
  const [animated, setAnimated] = useState(false);
  const [badgeVisible, setBadgeVisible] = useState(false);

  const homeXGDisplay = useCounter(
    prediction.expected_home_goals,
    600,
    !prefersReducedMotion,
  );
  const awayXGDisplay = useCounter(
    prediction.expected_away_goals,
    600,
    !prefersReducedMotion,
  );

  const probs = normaliseProbs(
    prediction.home_win_probability,
    prediction.draw_probability,
    prediction.away_win_probability,
  );

  const bars = [
    { label: 'Home Win', value: probs.homeWin, color: '#00D68F', delay: 0 },
    { label: 'Draw', value: probs.draw, color: '#F5A623', delay: 150 },
    { label: 'Away Win', value: probs.awayWin, color: '#097aff', delay: 300 },
  ] as const;

  const dominantLabel = bars.reduce((a, b) => (a.value >= b.value ? a : b)).label;

  const outcome: Outcome =
    probs.homeWin >= probs.awayWin && probs.homeWin >= probs.draw
      ? 'home'
      : probs.awayWin > probs.homeWin && probs.awayWin > probs.draw
        ? 'away'
        : 'draw';

  const badgeText: Record<Outcome, string> = {
    home: `PREDICTED: ${homeTeam.name.toUpperCase()} WIN · ${probs.homeWin}%`,
    draw: `PREDICTED: DRAW · ${probs.draw}%`,
    away: `PREDICTED: ${awayTeam.name.toUpperCase()} WIN · ${probs.awayWin}%`,
  };

  useEffect(() => {
    if (prefersReducedMotion) {
      setVisible(true);
      setAnimated(true);
      setBadgeVisible(true);
      return;
    }

    setVisible(false);
    setAnimated(false);
    setBadgeVisible(false);

    const tVisible = window.setTimeout(() => setVisible(true), 20);
    const tAnimated = window.setTimeout(() => setAnimated(true), 50);
    const tBadge = window.setTimeout(() => setBadgeVisible(true), 1000);

    return () => {
      window.clearTimeout(tVisible);
      window.clearTimeout(tAnimated);
      window.clearTimeout(tBadge);
    };
  }, [prediction, prefersReducedMotion]);

  const homeHigher = prediction.expected_home_goals > prediction.expected_away_goals;
  const awayHigher = prediction.expected_away_goals > prediction.expected_home_goals;

  return (
    <div
      className={`rounded-2xl border border-[#1e2a6e] bg-[#121845] p-6 transition-all ease-out ${
        visible || prefersReducedMotion
          ? 'translate-y-0 opacity-100 duration-[350ms]'
          : 'translate-y-5 opacity-0 duration-[350ms]'
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white"
            style={{ backgroundColor: homeTeam.color }}
          >
            {homeTeam.name.charAt(0).toUpperCase()}
          </div>
          <span className="truncate text-sm font-bold text-white">
            {homeTeam.name}
          </span>
        </div>

        <span className="shrink-0 text-xs text-[#8891B8]">vs</span>

        <div className="flex min-w-0 items-center justify-end gap-2">
          <span className="truncate text-right text-sm font-bold text-white">
            {awayTeam.name}
          </span>
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white"
            style={{ backgroundColor: awayTeam.color }}
          >
            {awayTeam.name.charAt(0).toUpperCase()}
          </div>
        </div>
      </div>

      <div className="my-4 border-t border-[#1e2a6e]" />

      <div className="grid grid-cols-3 items-end text-center">
        <div className="flex justify-center">
          <div
            className={`border-b-2 px-1 ${
              homeHigher ? 'border-[#00D68F]' : 'border-transparent'
            }`}
          >
            <span className="text-4xl font-bold tabular-nums text-white">
              {homeXGDisplay.toFixed(1)}
            </span>
          </div>
        </div>

        <div className="pb-1 text-[10px] font-bold uppercase tracking-[4px] text-[#8891B8]">
          xG
        </div>

        <div className="flex justify-center">
          <div
            className={`border-b-2 px-1 ${
              awayHigher ? 'border-[#00D68F]' : 'border-transparent'
            }`}
          >
            <span className="text-4xl font-bold tabular-nums text-white">
              {awayXGDisplay.toFixed(1)}
            </span>
          </div>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {bars.map((bar) => (
          <ProbabilityBar
            key={bar.label}
            label={bar.label}
            value={bar.value}
            color={bar.color}
            isDominant={bar.label === dominantLabel}
            delay={prefersReducedMotion ? 0 : bar.delay}
            animated={prefersReducedMotion ? true : animated}
          />
        ))}
      </div>

      <div className="mt-5 flex justify-center">
        <div
          className={`max-w-full truncate rounded-full border px-6 py-2 text-center text-xs font-bold tracking-wide transition-opacity duration-300 ${
            BADGE_STYLES[outcome]
          } ${badgeVisible || prefersReducedMotion ? 'opacity-100' : 'opacity-0'}`}
          title={badgeText[outcome]}
        >
          {badgeText[outcome]}
        </div>
      </div>

      <div className="mt-5 border-t border-[#1e2a6e] pt-4 text-center text-[10px] tracking-wide text-[#8891B8]">
        Based on last 10 matches · Model {prediction.model_version} · Powered by
        {' '}DataDerby
      </div>

      <div className="mt-4 text-center">
        <button
          type="button"
          onClick={onReset}
          className="text-xs text-[#8891B8] transition-colors hover:text-white"
        >
          ← New Prediction
        </button>
      </div>
    </div>
  );
}
