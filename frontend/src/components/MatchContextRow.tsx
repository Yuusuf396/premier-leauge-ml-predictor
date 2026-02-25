import type { Team } from '../types/api';

const CURRENT_SEASON_LABEL = '2025-26';

interface MatchContextRowProps {
  homeTeam: Team;
  awayTeam: Team;
}

export function MatchContextRow({
  homeTeam,
  awayTeam,
}: MatchContextRowProps) {
  void homeTeam;
  void awayTeam;

  return (
    <div className="py-1 text-center text-xs text-[#8891B8]">
      🏟 Premier League · {CURRENT_SEASON_LABEL}
    </div>
  );
}
