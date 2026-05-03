import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Zap } from 'lucide-react'
import { usePlayers } from '@/hooks/usePlayers'
import { getFranchise } from '@/constants/franchises'
import PlayerPool from '@/components/players/PlayerPool'
import AppNav from '@/components/layout/AppNav'

interface MatchProps {
  teamA: string
  teamB: string
}

function roleKey(role: string): 'WK' | 'BAT' | 'AR' | 'BOWL' | null {
  const r = role.toLowerCase()
  if (r.includes('wicket') || r === 'wk' || r === 'wk-batter') return 'WK'
  if (r.includes('bat') && !r.includes('all')) return 'BAT'
  if (r.includes('all')) return 'AR'
  if (r.includes('bowl')) return 'BOWL'
  return null
}

function CreditsBar({ players }: { players: ReturnType<typeof usePlayers>['players'] }) {
  const active = players.filter(p => p.is_active)
  const creditsUsed = active.reduce((s, p) => s + p.credits, 0)
  const BUDGET = 100
  const pct = Math.min((creditsUsed / BUDGET) * 100, 100)
  const barColor = pct >= 90 ? '#ef4444' : pct >= 75 ? '#f59e0b' : '#00c896'

  const counts = { WK: 0, BAT: 0, AR: 0, BOWL: 0 }
  for (const p of active) {
    const k = roleKey(p.role)
    if (k) counts[k]++
  }

  return (
    <div
      className="sticky z-40 border-b px-4 sm:px-6 py-2"
      style={{ top: 52, background: '#10151e', borderColor: 'rgba(255,255,255,0.06)' }}
    >
      <div className="max-w-screen-2xl mx-auto flex items-center gap-4 flex-wrap">
        {/* Credits */}
        <div className="flex items-center gap-2 min-w-[160px]">
          <span className="text-xs text-slate-500 shrink-0">Credits</span>
          <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.07)' }}>
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{ width: `${pct}%`, background: barColor }}
            />
          </div>
          <span className="text-xs font-bold tabular-nums" style={{ color: barColor }}>
            {creditsUsed.toFixed(1)}<span className="text-slate-600 font-normal"> / {BUDGET}</span>
          </span>
        </div>

        {/* Role counts */}
        <div className="flex items-center gap-3 text-xs flex-wrap">
          {([['WK', '#ec4899'], ['BAT', '#3b82f6'], ['AR', '#8b5cf6'], ['BOWL', '#f59e0b']] as const).map(([role, color]) => (
            <span key={role} className="flex items-center gap-1">
              <span className="font-bold" style={{ color }}>{role}</span>
              <span className="text-slate-400 font-semibold">{counts[role]}</span>
            </span>
          ))}
          <span className="text-slate-500">·</span>
          <span className="text-slate-400">
            Active <span className="font-bold text-white">{active.length}</span>
          </span>
        </div>
      </div>
    </div>
  )
}

export function Match({ teamA, teamB }: MatchProps) {
  const navigate = useNavigate()
  const { players, loading, error, benchPlayer, reinstatePlayer } = usePlayers(teamA, teamB)

  const franchiseA = getFranchise(teamA)
  const franchiseB = getFranchise(teamB)

  if (!teamA || !teamB) {
    navigate('/')
    return null
  }

  return (
    <div className="min-h-screen" style={{ background: '#0a0c10' }}>
      {/* Ambient gradient */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          background: `radial-gradient(ellipse 60% 30% at 0% 0%, ${franchiseA.primary}10, transparent 60%), radial-gradient(ellipse 60% 30% at 100% 0%, ${franchiseB.primary}10, transparent 60%)`,
        }}
      />

      <AppNav teamA={teamA} teamB={teamB} />
      <CreditsBar players={players} />

      {/* Main content */}
      <main className="relative z-10 max-w-screen-2xl mx-auto px-4 sm:px-6 py-6">
        {/* Page header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="mb-6 flex items-end justify-between"
        >
          <div>
            <h1 className="text-2xl font-black text-white tracking-tight">Player Pool</h1>
            <p className="text-slate-500 text-sm mt-1">
              Browse, filter, and bench players before generating your XI.
            </p>
          </div>

          {/* Generate XI */}
          <motion.button
            onClick={() => navigate('/results')}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            className="hidden sm:flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm text-white"
            style={{ background: 'linear-gradient(135deg, #00c896, #00a07a)', boxShadow: '0 0 20px rgba(0,200,150,0.3)' }}
          >
            <Zap className="w-4 h-4" />
            Generate XI →
          </motion.button>
        </motion.div>

        {/* Error state */}
        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mb-6 p-4 rounded-xl border text-sm"
            style={{ background: 'rgba(239,68,68,0.08)', borderColor: 'rgba(239,68,68,0.2)', color: '#f87171' }}
          >
            {error}
          </motion.div>
        )}

        {/* Player pool */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.1 }}
        >
          <PlayerPool
            players={players}
            teamA={teamA}
            teamB={teamB}
            onBench={benchPlayer}
            onReinstate={reinstatePlayer}
            loading={loading}
          />
        </motion.div>
      </main>

      {/* Sticky bottom CTA on mobile */}
      <div className="fixed bottom-0 inset-x-0 z-40 p-4 sm:hidden bg-gradient-to-t from-[#0a0c10] to-transparent">
        <motion.button
          onClick={() => navigate('/results')}
          whileTap={{ scale: 0.97 }}
          className="w-full py-3.5 rounded-xl font-bold text-white text-sm flex items-center justify-center gap-2"
          style={{ background: 'linear-gradient(135deg, #00c896, #00a07a)', boxShadow: '0 0 24px rgba(0,200,150,0.3)' }}
        >
          <Zap className="w-4 h-4" />
          Generate Fantasy XI →
        </motion.button>
      </div>
    </div>
  )
}
