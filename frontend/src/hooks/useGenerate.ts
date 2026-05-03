import { useState, useCallback, useRef } from 'react'
import { api } from '@/api/client'
import type { GenerateResult, EvoPoint, SSEEvent } from '@/types'

export type GenerateStatus = 'idle' | 'running' | 'done' | 'error'

export interface EvoProgress {
  safe: EvoPoint[]
  explosive: EvoPoint[]
  balanced: EvoPoint[]
}

export function useGenerate() {
  const [status, setStatus] = useState<GenerateStatus>('idle')
  const [progress, setProgress] = useState<EvoProgress>({ safe: [], explosive: [], balanced: [] })
  const [result, setResult] = useState<GenerateResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [currentStrategy, setCurrentStrategy] = useState<string>('')
  const esRef = useRef<EventSource | null>(null)

  const generate = useCallback(async (teamA: string, teamB: string) => {
    if (esRef.current) esRef.current.close()

    setStatus('running')
    setProgress({ safe: [], explosive: [], balanced: [] })
    setResult(null)
    setError(null)
    setCurrentStrategy('safe')

    try {
      const { run_id } = await api.startGenerate(teamA, teamB)
      const es = new EventSource(`/api/stream/${run_id}`)
      esRef.current = es

      es.onmessage = (e: MessageEvent) => {
        const data: SSEEvent = JSON.parse(e.data)

        if (data.type === 'progress') {
          setCurrentStrategy(data.strategy)
          setProgress(prev => ({
            ...prev,
            [data.strategy]: [
              ...(prev[data.strategy as keyof EvoProgress] || []),
              { generation: data.generation, fitness: data.fitness },
            ],
          }))
        } else if (data.type === 'complete') {
          const { type: _t, ...rest } = data as any
          setResult(rest as GenerateResult)
          setStatus('done')
          es.close()
        } else if (data.type === 'error') {
          setError(data.error)
          setStatus('error')
          es.close()
        }
      }

      es.onerror = () => {
        setError('Connection lost. Please try again.')
        setStatus('error')
        es.close()
      }
    } catch (e) {
      setError(String(e))
      setStatus('error')
    }
  }, [])

  const reset = useCallback(() => {
    if (esRef.current) esRef.current.close()
    setStatus('idle')
    setProgress({ safe: [], explosive: [], balanced: [] })
    setResult(null)
    setError(null)
  }, [])

  return { status, progress, result, error, currentStrategy, generate, reset }
}
