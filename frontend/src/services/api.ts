import type {
  ApiError,
  ApiHealth,
  ApiSeason,
  ApiTeam,
  PredictionRequest,
  PredictionResponse,
  Team,
} from '../types/api';

export const API_BASE =
  (import.meta as { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL ?? '';


export const CURRENT_SEASON = '2025-26';
export const MIN_LOAD_MS = 1500;

const TEAM_COLOR_MAP: Record<string, string> = {
  Arsenal: '#EF0107',
  'Aston Villa': '#95BFE5',
  Brentford: '#e30613',
  Brighton: '#0057B8',
  Burnley: '#6C1D45',
  Chelsea: '#034694',
  'Crystal Palace': '#1B458F',
  Everton: '#003399',
  Fulham: '#CC0000',
  Liverpool: '#C8102E',
  'Luton Town': '#F78F1E',
  'Manchester City': '#6CABDD',
  'Manchester United': '#DA291C',
  'Newcastle United': '#241F20',
  'Nottingham Forest': '#DD0000',
  'Sheffield United': '#EE2737',
  'Tottenham Hotspur': '#132257',
  'West Ham United': '#7A263A',
  'Wolverhampton Wanderers': '#FDB913',
  Bournemouth: '#DA291C',
};

export class ApiRequestError extends Error {
  constructor(
    public readonly httpStatus: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = 'ApiRequestError';
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  let data: unknown;
  try {
    data = await res.json();
  } catch {
    data = null;
  }

  if (!res.ok) {
    const err = (data ?? {}) as Partial<ApiError>;
    throw new ApiRequestError(
      res.status,
      err.error ?? 'request_failed',
      err.message ?? 'Request failed.',
    );
  }

  return data as T;
}

export function enrichTeam(apiTeam: ApiTeam): Team {
  return {
    ...apiTeam,
    color: TEAM_COLOR_MAP[apiTeam.name] ?? '#8891B8',
    short: apiTeam.name.slice(0, 3).toUpperCase(),
  };
}

export async function fetchHealth(): Promise<ApiHealth> {
  const res = await fetch(`${API_BASE}/api/health/`);
  return handleResponse<ApiHealth>(res);
}

export async function fetchTeams(): Promise<Team[]> {
  const res = await fetch(`${API_BASE}/api/teams/`);
  const data = await handleResponse<ApiTeam[]>(res);
  return data.map(enrichTeam);
}

export async function fetchSeasons(): Promise<ApiSeason[]> {
  const res = await fetch(`${API_BASE}/api/seasons/`);
  return handleResponse<ApiSeason[]>(res);
}

export async function postPrediction(
  homeTeam: Team,
  awayTeam: Team,
): Promise<PredictionResponse> {
  const body: PredictionRequest = {
    home_team: homeTeam.name,
    away_team: awayTeam.name,
    season: CURRENT_SEASON,
    match_date: new Date().toISOString().split('T')[0],
  };

  const res = await fetch(`${API_BASE}/api/predict/match`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  return handleResponse<PredictionResponse>(res);
}
