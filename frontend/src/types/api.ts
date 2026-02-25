export interface ApiTeam {
  id: number;
  name: string;
}

export interface ApiSeason {
  label: string;
}

export interface ApiHealth {
  status: string;
  artifact_loaded?: boolean;
  model_version?: string;
  error?: string;
}

export interface PredictionRequest {
  home_team: string;
  away_team: string;
  season?: string;
  match_date: string;
}

export interface PredictionResponse {
  home_team: string;
  away_team: string;
  expected_home_goals: number;
  expected_away_goals: number;
  home_win_probability: number;
  draw_probability: number;
  away_win_probability: number;
  model_version: string;
  features: Record<string, unknown>;
}

export type ErrorCode =
  | 'invalid_input'
  | 'not_found'
  | 'insufficient_history'
  | 'model_not_found'
  | 'prediction_unavailable'
  | 'forbidden'
  | 'request_failed'
  | 'model_not_loaded'
  | 'metadata_missing'
  | 'feature_list_missing'
  | 'data_not_found'
  | 'data_load_failed';

export interface ApiError {
  error: ErrorCode;
  message: string;
}

export interface ApiModelVersion {
  id: number;
  version: string;
  artifact_path: string;
  selected_model_name: string;
  calibration_method: string;
  val_log_loss: number | null;
  val_accuracy: number | null;
  is_active: boolean;
  created_at: string;
}

export interface Team extends ApiTeam {
  color: string;
  short: string;
}

export interface NormalisedProbs {
  homeWin: number;
  draw: number;
  awayWin: number;
}

export type Outcome = 'home' | 'draw' | 'away';
