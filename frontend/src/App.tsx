import { Routes, Route, Navigate } from 'react-router-dom'
import { useState } from 'react'
import { Home } from '@/pages/Home'
import { Match } from '@/pages/Match'
import { Results } from '@/pages/Results'
import { getFranchise } from '@/constants/franchises'

export interface AppState {
  teamA: string
  teamB: string
}

const SESSION_KEY = 'dg_match'

function readSession(): AppState | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY)
    return raw ? (JSON.parse(raw) as AppState) : null
  } catch {
    return null
  }
}

function writeSession(state: AppState | null) {
  if (state) sessionStorage.setItem(SESSION_KEY, JSON.stringify(state))
  else sessionStorage.removeItem(SESSION_KEY)
}

export default function App() {
  const [match, setMatch] = useState<AppState | null>(readSession)

  function handleMatchSelect(state: AppState) {
    setMatch(state)
    writeSession(state)
  }

  // Inject franchise CSS vars whenever teams change
  const style = match
    ? ({
        '--team-a': getFranchise(match.teamA).primary,
        '--team-a-rgb': hexToRgb(getFranchise(match.teamA).primary),
        '--team-b': getFranchise(match.teamB).primary,
        '--team-b-rgb': hexToRgb(getFranchise(match.teamB).primary),
      } as React.CSSProperties)
    : {}

  return (
    <div style={style} className="min-h-screen bg-[var(--bg-primary)]">
      <Routes>
        <Route path="/" element={<Home onMatchSelect={handleMatchSelect} />} />
        <Route
          path="/match"
          element={
            match ? (
              <Match teamA={match.teamA} teamB={match.teamB} />
            ) : (
              <Navigate to="/" replace />
            )
          }
        />
        <Route
          path="/results"
          element={
            match ? (
              <Results teamA={match.teamA} teamB={match.teamB} />
            ) : (
              <Navigate to="/" replace />
            )
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

function hexToRgb(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `${r}, ${g}, ${b}`
}
