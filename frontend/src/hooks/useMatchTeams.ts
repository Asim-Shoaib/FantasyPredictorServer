import { useState, useEffect } from 'react'
import { api } from '@/api/client'

export function useMatchTeams() {
  const [teams, setTeams] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getTeams()
      .then(setTeams)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return { teams, loading, error }
}
