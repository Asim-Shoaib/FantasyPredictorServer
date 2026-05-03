import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, Zap } from 'lucide-react'
import { usePlayers } from '@/hooks/usePlayers'
import { getFranchise } from '@/constants/franchises'
import PlayerPool from '@/components/players/PlayerPool'

interface MatchProps {
  teamA: string
  teamB: string
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
    <div className="min-h-screen" style={{ background: '#0a0a0f' }}>
      {/* Ambient gradient from team colors */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          background: `radial-gradient(ellipse 60% 30% at 0% 0%, ${franchiseA.primary}14, transparent 60%), radial-gradient(ellipse 60% 30% at 100% 0%, ${franchiseB.primary}14, transparent 60%)`,
        }}
      />

      {/* Top nav */}
      <motion.nav
        initial={{ opacity: 0, y: -16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="sticky top-0 z-30 border-b border-white/[0.06] bg-[#0a0a0f]/80 backdrop-blur-xl"
      >
        <div className="max-w-screen-2xl mx-auto px-4 sm:px-6 py-3 flex items-center gap-4">
          {/* Back */}
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-1.5 text-slate-500 hover:text-white transition-colors text-sm font-medium group"
          >
            <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
            Back
          </button>

          {/* Match banner */}
          <div className="flex-1 flex items-center justify-center gap-3">
            <div className="flex items-center gap-2">
              <span
                className="w-3 h-3 rounded-full"
                style={{ background: franchiseA.primary, boxShadow: `0 0 8px ${franchiseA.primary}` }}
              />
              <span className="text-sm font-bold text-white hidden sm:block">{teamA}</span>
              <span className="text-sm font-bold text-white sm:hidden">{franchiseA.shortName}</span>
            </div>

            <div className="px-3 py-0.5 rounded-full bg-white/[0.06] border border-white/[0.08]">
              <span className="text-xs font-black tracking-widest text-slate-400">VS</span>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-white hidden sm:block">{teamB}</span>
              <span className="text-sm font-bold text-white sm:hidden">{franchiseB.shortName}</span>
              <span
                className="w-3 h-3 rounded-full"
                style={{ background: franchiseB.primary, boxShadow: `0 0 8px ${franchiseB.primary}` }}
              />
            </div>
          </div>

          {/* Generate XI button */}
          <motion.button
            onClick={() => navigate('/results')}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            className="flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-sm text-white transition-all"
            style={{
              background: `linear-gradient(135deg, ${franchiseA.primary}, ${franchiseB.primary})`,
              boxShadow: `0 0 20px ${franchiseA.primary}40`,
            }}
          >
            <Zap className="w-4 h-4" />
            <span className="hidden sm:inline">Generate XI</span>
            <span className="sm:hidden">Gen XI</span>
            <span className="hidden sm:inline">→</span>
          </motion.button>
        </div>
      </motion.nav>

      {/* Main content */}
      <main className="relative z-10 max-w-screen-2xl mx-auto px-4 sm:px-6 py-6">
        {/* Page header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="mb-6"
        >
          <h1 className="text-2xl font-black text-white tracking-tight">
            Player Pool
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Browse, filter, and bench players before generating your XI.
          </p>
        </motion.div>

        {/* Error state */}
        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm"
          >
            {error}
          </motion.div>
        )}

        {/* Player pool */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.2 }}
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
      <div className="fixed bottom-0 inset-x-0 z-40 p-4 sm:hidden bg-gradient-to-t from-[#0a0a0f] to-transparent">
        <motion.button
          onClick={() => navigate('/results')}
          whileTap={{ scale: 0.97 }}
          className="w-full py-3.5 rounded-xl font-bold text-white text-sm flex items-center justify-center gap-2"
          style={{
            background: `linear-gradient(135deg, ${franchiseA.primary}, ${franchiseB.primary})`,
          }}
        >
          <Zap className="w-4 h-4" />
          Generate Fantasy XI →
        </motion.button>
      </div>
    </div>
  )
}
