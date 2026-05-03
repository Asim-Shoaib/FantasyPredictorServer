import type { PlayerProfile } from '@/types'

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

  startGenerate: async (teamA: string, teamB: string): Promise<StartGenerateResponse> => {
    const res = await fetch('/api/generate-teams-start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team_a: teamA, team_b: teamB }),
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
