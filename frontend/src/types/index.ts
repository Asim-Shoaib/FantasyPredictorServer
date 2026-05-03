export interface PlayerProfile {
  player_id: string
  player_name: string
  team: string
  role: string
  credits: number
  is_active: boolean
  form_state: 'cold' | 'avg' | 'hot' | 'unknown'
  form_probs: [number, number, number]
  form_source: 'general' | 'short_term'
  career_avg: number | null
  career_std: number | null
  career_variance: number | null
  rolling_avg: number | null
  rolling_window: number
  rolling_fallback: boolean
  adjusted_score: number | null
  elo_post: number | null
  elo_multiplier: number
  matches_in_history: number
  photo_url: string | null
}

export interface TeamPlayer extends PlayerProfile {
  is_captain: boolean
  is_vc: boolean
}

export interface TeamResult {
  strategy: 'safe' | 'explosive' | 'balanced'
  players: TeamPlayer[]
  captain: TeamPlayer
  vc: TeamPlayer
  total_credits: number
  fitness: number
  expected_score: number
  ceiling_score: number
  floor_score: number
  team_rolling_avg: number
  team_hot_prob: number
}

export interface GenerateResult {
  run_id: string
  match: { team_a: string; team_b: string }
  safe: TeamResult
  explosive: TeamResult
  balanced: TeamResult
}

export type SSEEvent =
  | { type: 'progress'; strategy: string; generation: number; fitness: number }
  | { type: 'complete'; run_id: string; match: { team_a: string; team_b: string }; safe: TeamResult; explosive: TeamResult; balanced: TeamResult }
  | { type: 'error'; error: string }

export interface EvoPoint {
  generation: number
  fitness: number
}

export type RoleFilter = 'all' | 'wk' | 'bat' | 'ar' | 'bowl'
export type TeamFilter = 'all' | 'a' | 'b'
