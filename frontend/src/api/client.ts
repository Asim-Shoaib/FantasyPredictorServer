import type { PlayerProfile } from '@/types'
import type { Constraints } from '@/components/constraints/ConstraintsForm'

export interface StartGenerateResponse { run_id: string }

export const api = {
  getTeams: async (): Promise<string[]> => {
    const res = await fetch('/api/match/teams')
    if (!res.ok) throw new Error(`Failed to fetch teams: ${res.status}`)
    return res.json()
  },

  getPlayers: async (teamA: string, teamB: string): Promise<PlayerProfile[]> => {
    const res = await fetch(
      `/api/players?team_a=${encodeURIComponent(teamA)}&team_b=${encodeURIComponent(teamB)}`
    )
    if (!res.ok) throw new Error(`Failed to fetch players: ${res.status}`)
    return res.json()
  },

  startGenerate: async (teamA: string, teamB: string, constraints: Constraints): Promise<StartGenerateResponse> => {
    const res = await fetch('/api/generate-teams-start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        team_a: teamA, 
        team_b: teamB,
        constraints: {
          budget: constraints.budget,
          batter_min: constraints.batter_min,
          batter_max: constraints.batter_max,
          allrounder_min: constraints.allrounder_min,
          allrounder_max: constraints.allrounder_max,
          wicketkeeper_min: constraints.wicketkeeper_min,
          wicketkeeper_max: constraints.wicketkeeper_max,
          bowler_min: constraints.bowler_min,
          bowler_max: constraints.bowler_max,
          per_team_min: constraints.per_team_min,
          per_team_max: constraints.per_team_max,
        },
      }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error((err as any).error || `Failed to start: ${res.status}`)
    }
    return res.json()
  },

  benchPlayer: async (playerId: string): Promise<void> => {
    await fetch(`/api/roster/bench/${encodeURIComponent(playerId)}`, { method: 'POST' })
  },

  reinstatePlayer: async (playerId: string): Promise<void> => {
    await fetch(`/api/roster/reinstate/${encodeURIComponent(playerId)}`, { method: 'POST' })
  },

  health: async (): Promise<boolean> => {
    try {
      const res = await fetch('/api/health')
      return res.ok
    } catch {
      return false
    }
  },
}
