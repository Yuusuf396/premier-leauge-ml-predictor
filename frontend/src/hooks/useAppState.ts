import { useCallback, useEffect, useReducer } from 'react';
import {
  ApiRequestError,
  MIN_LOAD_MS,
  enrichTeam,
  fetchHealth,
  fetchTeams,
  postPrediction,
} from '../services/api';
import type { PredictionResponse, Team } from '../types/api';

export type AppStatus =
  | 'boot'
  | 'idle'
  | 'ready'
  | 'loading'
  | 'result'
  | 'error';

export interface AppState {
  status: AppStatus;
  teams: Team[];
  homeTeam: Team | null;
  awayTeam: Team | null;
  prediction: PredictionResponse | null;
  error: { message: string } | null;
  backendUp: boolean | null;
}

const init: AppState = {
  status: 'boot',
  teams: [],
  homeTeam: null,
  awayTeam: null,
  prediction: null,
  error: null,
  backendUp: null,
};

type Action =
  | { type: 'BOOT_SUCCESS'; teams: Team[] }
  | { type: 'BOOT_FAILURE'; teams: Team[] }
  | { type: 'SELECT_HOME'; team: Team }
  | { type: 'SELECT_AWAY'; team: Team }
  | { type: 'CLEAR_HOME' }
  | { type: 'CLEAR_AWAY' }
  | { type: 'GENERATE' }
  | { type: 'RESOLVE'; prediction: PredictionResponse }
  | { type: 'REJECT'; error: { message: string } }
  | { type: 'RESET' };

function isReady(home: Team | null, away: Team | null): boolean {
  return home !== null && away !== null;
}

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'BOOT_SUCCESS':
      return { ...state, status: 'idle', teams: action.teams, backendUp: true };
    case 'BOOT_FAILURE':
      return { ...state, status: 'idle', teams: action.teams, backendUp: false };
    case 'SELECT_HOME':
      return {
        ...state,
        homeTeam: action.team,
        status: isReady(action.team, state.awayTeam) ? 'ready' : 'idle',
      };
    case 'SELECT_AWAY':
      return {
        ...state,
        awayTeam: action.team,
        status: isReady(state.homeTeam, action.team) ? 'ready' : 'idle',
      };
    case 'CLEAR_HOME':
      return { ...state, homeTeam: null, status: 'idle' };
    case 'CLEAR_AWAY':
      return { ...state, awayTeam: null, status: 'idle' };
    case 'GENERATE':
      return { ...state, status: 'loading', prediction: null, error: null };
    case 'RESOLVE':
      return { ...state, status: 'result', prediction: action.prediction };
    case 'REJECT':
      return { ...state, status: 'error', error: action.error };
    case 'RESET':
      return {
        ...init,
        status: 'idle',
        teams: state.teams,
        backendUp: state.backendUp,
      };
    default:
      return state;
  }
}

const ERROR_MESSAGES: Record<string, string> = {
  invalid_input: 'Please check your team selection and try again.',
  not_found: 'One of the selected teams could not be found.',
  insufficient_history:
    'Not enough match history to generate a prediction for this fixture.',
  model_not_found: 'The prediction model is currently unavailable.',
  prediction_unavailable:
    'The prediction engine encountered an unexpected error.',
  forbidden: 'You do not have permission to perform this action.',
  request_failed: "We couldn't generate a prediction. Please try again.",
  model_not_loaded: 'The backend is up, but the model is not loaded yet.',
  metadata_missing: 'Model metadata is missing on the backend.',
  feature_list_missing: 'Model feature configuration is missing on the backend.',
  data_not_found: 'Match data is unavailable on the backend.',
  data_load_failed: 'The backend could not load match data.',
};

function resolveErrorMessage(err: unknown): string {
  if (err instanceof ApiRequestError) {
    return ERROR_MESSAGES[err.code] ?? err.message ?? ERROR_MESSAGES.request_failed;
  }
  return ERROR_MESSAGES.request_failed;
}

const TEAMS_FALLBACK: Team[] = [
  { id: 1, name: 'Arsenal' },
  { id: 2, name: 'Aston Villa' },
  { id: 3, name: 'Brentford' },
  { id: 4, name: 'Brighton' },
  { id: 5, name: 'Burnley' },
  { id: 6, name: 'Chelsea' },
  { id: 7, name: 'Crystal Palace' },
  { id: 8, name: 'Everton' },
  { id: 9, name: 'Fulham' },
  { id: 10, name: 'Liverpool' },
  { id: 11, name: 'Luton Town' },
  { id: 12, name: 'Manchester City' },
  { id: 13, name: 'Manchester United' },
  { id: 14, name: 'Newcastle United' },
  { id: 15, name: 'Nottingham Forest' },
  { id: 16, name: 'Sheffield United' },
  { id: 17, name: 'Tottenham Hotspur' },
  { id: 18, name: 'West Ham United' },
  { id: 19, name: 'Wolverhampton Wanderers' },
  { id: 20, name: 'Bournemouth' },
].map(enrichTeam);

export function useAppState() {
  const [state, dispatch] = useReducer(reducer, init);

  useEffect(() => {
    let cancelled = false;

    async function boot() {
      let backendUp = false;
      let teams = TEAMS_FALLBACK;

      try {
        await fetchHealth();
        backendUp = true;
      } catch {
        // Stay in offline mode with fallback teams.
      }

      try {
        teams = await fetchTeams();
      } catch {
        // Use fallback teams silently.
      }

      if (cancelled) return;
      dispatch({ type: backendUp ? 'BOOT_SUCCESS' : 'BOOT_FAILURE', teams });
    }

    void boot();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleGenerate = useCallback(async () => {
    if (!state.homeTeam || !state.awayTeam) return;

    dispatch({ type: 'GENERATE' });

    const minDelay = new Promise<void>((resolve) =>
      window.setTimeout(resolve, MIN_LOAD_MS),
    );
    const predictionPromise = postPrediction(state.homeTeam, state.awayTeam);

    try {
      const [prediction] = await Promise.all([predictionPromise, minDelay]);
      dispatch({ type: 'RESOLVE', prediction });
    } catch (err) {
      await minDelay.catch(() => undefined);
      dispatch({ type: 'REJECT', error: { message: resolveErrorMessage(err) } });
    }
  }, [state.homeTeam, state.awayTeam]);

  return { state, dispatch, handleGenerate };
}
