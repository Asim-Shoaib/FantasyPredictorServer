import { useState, useEffect, useCallback } from 'react'
import { api } from '@/api/client'
import type { PlayerProfile } from '@/types'

export function usePlayers(teamA: string | null, teamB: string | null) {
  const [players, setPlayers] = useState<PlayerProfile[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!teamA || !teamB) return
    setLoading(true)
    setError(null)
    api.getPlayers(teamA, teamB)
      .then(setPlayers)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [teamA, teamB])

  const benchPlayer = useCallback((id: string) => {
    api.benchPlayer(id)
    setPlayers(prev =>
      prev.map(p => (p.player_id === id ? { ...p, is_active: false } : p))
    )
  }, [])

  const reinstatePlayer = useCallback((id: string) => {
    api.reinstatePlayer(id)
    setPlayers(prev =>
      prev.map(p => (p.player_id === id ? { ...p, is_active: true } : p))
    )
  }, [])

  return { players, loading, error, benchPlayer, reinstatePlayer }
}
