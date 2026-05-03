import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { RefreshCw, ArrowLeft, AlertTriangle } from 'lucide-react'
import { useGenerate } from '@/hooks/useGenerate'
import { getFranchise } from '@/constants/franchises'
import EvolutionDashboard from '@/components/evolution/EvolutionDashboard'
import WarRoom from '@/components/warroom/WarRoom'

interface ResultsProps {
  teamA: string
  teamB: string
}

export function Results({ teamA, teamB }: ResultsProps) {
  const navigate = useNavigate()
  const { status, progress, result, error, currentStrategy, generate, reset } = useGenerate()

  const franchiseA = getFranchise(teamA)
  const franchiseB = getFranchise(teamB)

  // Kick off generation immediately on mount
  useEffect(() => {
    if (teamA && teamB) {
      generate(teamA, teamB)
    }
    // Cleanup on unmount — reset to avoid stale state if user navigates back
    return () => {
      reset()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [teamA, teamB])

  function handleRetry() {
    reset()
    generate(teamA, teamB)
  }

  // Guard: if no teams set, redirect home
  if (!teamA || !teamB) {
    navigate('/')
    return null
  }

  return (
    <div className="min-h-screen" style={{ background: '#0a0a0f' }}>
      {/* Sticky minimal top bar visible during evolution */}
      <AnimatePresence>
        {status === 'running' && (
          <motion.nav
            key="evo-nav"
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            transition={{ duration: 0.35 }}
            className="fixed top-0 left-0 right-0 z-50 border-b border-white/[0.06] bg-[#0a0a0f]/90 backdrop-blur-xl"
          >
            <div className="max-w-screen-2xl mx-auto px-4 sm:px-6 py-2.5 flex items-center gap-4">
              <button
                onClick={() => navigate('/match')}
                className="flex items-center gap-1.5 text-slate-500 hover:text-white transition-colors text-sm font-medium group"
              >
                <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
                <span className="hidden sm:inline">Back to Pool</span>
              </button>

              <div className="flex-1 flex items-center justify-center gap-2">
                <div
                  className="w-2 h-2 rounded-full animate-pulse"
                  style={{ background: '#22c55e', boxShadow: '0 0 6px #22c55e' }}
                />
                <span className="text-xs font-bold tracking-widest uppercase text-slate-400">
                  Genetic Algorithm Running
                </span>
              </div>

              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1.5">
                  <span
                    className="text-xs font-bold"
                    style={{ color: franchiseA.primary }}
                  >
                    {franchiseA.shortName}
                  </span>
                  <span className="text-xs text-slate-600">vs</span>
                  <span
                    className="text-xs font-bold"
                    style={{ color: franchiseB.primary }}
                  >
                    {franchiseB.shortName}
                  </span>
                </div>
              </div>
            </div>
          </motion.nav>
        )}
      </AnimatePresence>

      {/* Phase transitions */}
      <AnimatePresence mode="wait">
        {/* PHASE 1: Evolution running */}
        {status === 'running' && (
          <motion.div
            key="evolution"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            transition={{ duration: 0.4 }}
            className="pt-10"
          >
            <EvolutionDashboard
              progress={progress}
              currentStrategy={currentStrategy}
              totalGenerations={150}
            />
          </motion.div>
        )}

        {/* PHASE 2: War room — results ready */}
        {status === 'done' && result && (
          <motion.div
            key="warroom"
            initial={{ opacity: 0, y: 32 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
          >
            <WarRoom result={result} />
          </motion.div>
        )}

        {/* Error state */}
        {status === 'error' && (
          <motion.div
            key="error"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35 }}
            className="min-h-screen flex flex-col items-center justify-center gap-8 px-6"
          >
            {/* Ambient glow */}
            <div
              className="pointer-events-none absolute inset-0"
              style={{
                background:
                  'radial-gradient(ellipse 60% 40% at 50% 50%, rgba(239,68,68,0.06) 0%, transparent 60%)',
              }}
            />

            <div className="relative z-10 flex flex-col items-center gap-6 max-w-md text-center">
              <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
                <AlertTriangle className="w-8 h-8 text-red-400" />
              </div>

              <div>
                <h2 className="text-2xl font-black text-white mb-2">Generation Failed</h2>
                <p className="text-slate-400 text-sm leading-relaxed">
                  {error || 'An unexpected error occurred while running the genetic algorithm.'}
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={() => navigate('/match')}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-slate-400 border border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.07] hover:text-white transition-all"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Back
                </button>
                <button
                  onClick={handleRetry}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm text-white transition-all"
                  style={{
                    background: `linear-gradient(135deg, ${franchiseA.primary}, ${franchiseB.primary})`,
                    boxShadow: `0 0 24px ${franchiseA.primary}40`,
                  }}
                >
                  <RefreshCw className="w-4 h-4" />
                  Retry
                </button>
              </div>
            </div>
          </motion.div>
        )}

        {/* Idle / loading initial state — shouldn't normally show */}
        {status === 'idle' && (
          <motion.div
            key="idle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="min-h-screen flex items-center justify-center"
          >
            <div className="flex flex-col items-center gap-4 text-slate-500">
              <div
                className="w-10 h-10 rounded-full border-2 border-t-transparent animate-spin"
                style={{ borderColor: `${franchiseA.primary}60`, borderTopColor: 'transparent' }}
              />
              <p className="text-sm font-medium tracking-wide">Initializing…</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
