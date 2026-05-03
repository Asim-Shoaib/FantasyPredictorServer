import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, Zap, Cpu, Brain, Dna } from 'lucide-react'
import { useMatchTeams } from '@/hooks/useMatchTeams'
import { getFranchise } from '@/constants/franchises'
import { cn } from '@/lib/utils'

interface HomeProps {
  onMatchSelect: (state: { teamA: string; teamB: string }) => void
}

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
}
const item = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
}

// ─── Custom franchise dropdown ────────────────────────────────────────────────
interface SelectorProps {
  teams: string[]
  value: string
  onChange: (t: string) => void
  placeholder: string
  exclude?: string
  side: 'a' | 'b'
}

function FranchiseSelector({ teams, value, onChange, placeholder, exclude, side }: SelectorProps) {
  const [open, setOpen] = useState(false)
  const [openUpward, setOpenUpward] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const franchise = value ? getFranchise(value) : null
  const available = teams.filter(t => t !== exclude)

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  function handleToggle() {
    if (!open && ref.current) {
      const rect = ref.current.getBoundingClientRect()
      const spaceBelow = window.innerHeight - rect.bottom
      setOpenUpward(spaceBelow < 300)
    }
    setOpen(o => !o)
  }

  return (
    <div ref={ref} className="relative w-full">
      {/* Trigger button */}
      <button
        onClick={handleToggle}
        className="w-full flex items-center gap-3 px-4 py-4 rounded-2xl text-left transition-all duration-300 outline-none"
        style={{
          background: franchise
            ? `linear-gradient(135deg, ${franchise.primary}22, ${franchise.secondary}14)`
            : 'rgba(255,255,255,0.05)',
          border: franchise
            ? `1px solid ${franchise.primary}55`
            : '1px solid rgba(255,255,255,0.1)',
          boxShadow: franchise ? `0 0 32px ${franchise.primary}20, inset 0 0 20px ${franchise.primary}06` : 'none',
        }}
      >
        {franchise ? (
          <>
            {/* Colored left accent */}
            <div
              className="absolute left-0 top-2 bottom-2 w-1 rounded-full"
              style={{ background: `linear-gradient(to bottom, ${franchise.primary}, ${franchise.secondary})` }}
            />
            <span className="text-2xl ml-1">{franchise.emoji}</span>
            <div className="flex-1 min-w-0">
              <p className="text-white font-bold text-sm truncate">{value}</p>
              <p className="text-xs font-medium mt-0.5" style={{ color: franchise.secondary }}>
                {franchise.shortName} · {side === 'a' ? 'Team A' : 'Team B'}
              </p>
            </div>
          </>
        ) : (
          <>
            <div className="w-10 h-10 rounded-xl bg-white/[0.06] flex items-center justify-center border border-white/[0.08] flex-shrink-0">
              <span className="text-slate-500 text-lg">🏏</span>
            </div>
            <span className="text-slate-400 text-sm font-medium flex-1">{placeholder}</span>
          </>
        )}
        <ChevronDown
          className={cn(
            'w-4 h-4 text-slate-500 transition-transform duration-200 flex-shrink-0',
            open && 'rotate-180'
          )}
        />
      </button>

      {/* Dropdown list */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: openUpward ? 8 : -8, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: openUpward ? 8 : -8, scale: 0.97 }}
            transition={{ duration: 0.15, ease: [0.22, 1, 0.36, 1] }}
            className="absolute left-0 right-0 z-50 rounded-2xl overflow-hidden"
            style={{
              ...(openUpward
                ? { bottom: 'calc(100% + 8px)' }
                : { top: 'calc(100% + 8px)' }),
              background: '#111118',
              border: '1px solid rgba(255,255,255,0.1)',
              boxShadow: '0 24px 64px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.04)',
              maxHeight: '260px',
              overflowY: 'auto',
            }}
          >
            {available.length === 0 && (
              <div className="px-4 py-6 text-center text-slate-500 text-sm">No teams available</div>
            )}
            {available.map((team, i) => {
              const f = getFranchise(team)
              const isSelected = team === value
              return (
                <motion.button
                  key={team}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04 }}
                  onClick={() => { onChange(team); setOpen(false) }}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-3 text-left transition-all duration-100',
                    'border-b border-white/[0.05] last:border-0',
                    isSelected ? 'bg-white/[0.08]' : 'hover:bg-white/[0.05]'
                  )}
                >
                  <div
                    className="w-1 h-8 rounded-full flex-shrink-0"
                    style={{ background: `linear-gradient(to bottom, ${f.primary}, ${f.secondary})` }}
                  />
                  <span className="text-xl flex-shrink-0">{f.emoji}</span>
                  <div className="flex-1 min-w-0">
                    <p className={cn('text-sm font-semibold truncate', isSelected ? 'text-white' : 'text-slate-200')}>
                      {team}
                    </p>
                    <p className="text-xs text-slate-500">{f.shortName}</p>
                  </div>
                  {isSelected && (
                    <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: f.primary }} />
                  )}
                </motion.button>
              )
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────
export function Home({ onMatchSelect }: HomeProps) {
  const navigate = useNavigate()
  const { teams, loading } = useMatchTeams()
  const [teamA, setTeamA] = useState('')
  const [teamB, setTeamB] = useState('')

  const franchiseA = teamA ? getFranchise(teamA) : null
  const franchiseB = teamB ? getFranchise(teamB) : null
  const canGenerate = teamA && teamB && teamA !== teamB

  function handleSubmit() {
    if (!canGenerate) return
    onMatchSelect({ teamA, teamB })
    navigate('/match')
  }

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden" style={{ background: '#08080e' }}>

      {/* Dot grid background */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.035) 1px, transparent 1px)',
          backgroundSize: '28px 28px',
        }}
      />

      {/* Static ambient glow */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse 90% 50% at 50% -5%, rgba(99,102,241,0.14) 0%, transparent 65%),' +
            'radial-gradient(ellipse 50% 30% at 15% 85%, rgba(14,165,233,0.07) 0%, transparent 55%),' +
            'radial-gradient(ellipse 50% 30% at 85% 85%, rgba(168,85,247,0.07) 0%, transparent 55%)',
        }}
      />

      {/* Dynamic team color blobs */}
      <AnimatePresence>
        {franchiseA && (
          <motion.div
            key={`blob-a-${teamA}`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.8 }}
            className="pointer-events-none absolute rounded-full blur-[120px]"
            style={{
              width: 500, height: 400,
              left: '-8%', top: '20%',
              background: franchiseA.primary + '28',
            }}
          />
        )}
        {franchiseB && (
          <motion.div
            key={`blob-b-${teamB}`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.8 }}
            className="pointer-events-none absolute rounded-full blur-[120px]"
            style={{
              width: 500, height: 400,
              right: '-8%', top: '20%',
              background: franchiseB.primary + '28',
            }}
          />
        )}
      </AnimatePresence>

      {/* Main content */}
      <motion.div
        className="relative z-10 flex flex-col items-center gap-8 px-6 w-full max-w-xl"
        variants={stagger}
        initial="hidden"
        animate="show"
      >
        {/* Status badge */}
        <motion.div variants={item}>
          <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-bold tracking-widest uppercase"
            style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.09)', color: '#94a3b8' }}>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            PSL 2026 · Season Active
          </span>
        </motion.div>

        {/* Title */}
        <motion.div variants={item} className="text-center select-none" style={{ lineHeight: 0.9 }}>
          <div
            className="text-[6rem] sm:text-[8rem] font-black tracking-tighter bg-clip-text text-transparent"
            style={{ backgroundImage: 'linear-gradient(160deg, #e2e8f0 0%, #94a3b8 60%, #cbd5e1 100%)' }}
          >
            DRAFT
          </div>
          <div
            className="text-[6rem] sm:text-[8rem] font-black tracking-tighter bg-clip-text text-transparent"
            style={{ backgroundImage: 'linear-gradient(135deg, #6366f1 0%, #22d3ee 45%, #a855f7 100%)' }}
          >
            GENIUS
          </div>
        </motion.div>

        {/* AI stack badges */}
        <motion.div variants={item} className="flex items-center gap-2 flex-wrap justify-center">
          {[
            { icon: Cpu, label: 'Elo Rating', color: '#6366f1' },
            { icon: Brain, label: 'HMM Form', color: '#22d3ee' },
            { icon: Dna, label: 'Genetic AI', color: '#a855f7' },
          ].map(({ icon: Icon, label, color }) => (
            <span
              key={label}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border"
              style={{ background: color + '12', borderColor: color + '30', color }}
            >
              <Icon className="w-3 h-3" />
              {label}
            </span>
          ))}
        </motion.div>

        {/* Team selectors */}
        {loading ? (
          <motion.div variants={item} className="flex items-center gap-3 text-slate-500 py-6">
            <div className="w-5 h-5 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
            <span className="text-sm tracking-wide">Loading squads…</span>
          </motion.div>
        ) : (
          <motion.div variants={item} className="w-full flex flex-col sm:flex-row items-stretch gap-3">
            <div className="flex-1">
              <FranchiseSelector
                teams={teams}
                value={teamA}
                onChange={setTeamA}
                placeholder="Select Team A"
                exclude={teamB}
                side="a"
              />
            </div>

            {/* VS pill */}
            <div className="flex sm:flex-col items-center justify-center py-1 sm:py-0">
              <motion.div
                animate={canGenerate ? { scale: [1, 1.12, 1] } : { scale: 1 }}
                transition={{ duration: 1.2, repeat: canGenerate ? Infinity : 0, repeatDelay: 1.5 }}
                className="px-3 py-1.5 rounded-full font-black text-sm tracking-widest"
                style={{
                  background: canGenerate
                    ? `linear-gradient(135deg, ${franchiseA!.primary}30, ${franchiseB!.primary}30)`
                    : 'rgba(255,255,255,0.05)',
                  border: canGenerate
                    ? `1px solid rgba(255,255,255,0.15)`
                    : '1px solid rgba(255,255,255,0.07)',
                  color: canGenerate ? '#fff' : '#475569',
                }}
              >
                VS
              </motion.div>
            </div>

            <div className="flex-1">
              <FranchiseSelector
                teams={teams}
                value={teamB}
                onChange={setTeamB}
                placeholder="Select Team B"
                exclude={teamA}
                side="b"
              />
            </div>
          </motion.div>
        )}

        {/* CTA */}
        <motion.div variants={item} className="w-full">
          <motion.button
            onClick={handleSubmit}
            disabled={!canGenerate}
            whileHover={canGenerate ? { scale: 1.02, y: -2 } : {}}
            whileTap={canGenerate ? { scale: 0.98 } : {}}
            className="relative w-full py-4 rounded-2xl font-bold text-base tracking-wide overflow-hidden transition-all duration-300"
            style={
              canGenerate
                ? {
                    background: `linear-gradient(135deg, ${franchiseA!.primary} 0%, ${franchiseA!.secondary} 35%, ${franchiseB!.secondary} 65%, ${franchiseB!.primary} 100%)`,
                    boxShadow: `0 0 48px ${franchiseA!.primary}50, 0 0 48px ${franchiseB!.primary}50, 0 4px 24px rgba(0,0,0,0.4)`,
                    color: '#fff',
                  }
                : {
                    background: 'rgba(255,255,255,0.04)',
                    border: '1px solid rgba(255,255,255,0.07)',
                    color: '#334155',
                    cursor: 'not-allowed',
                  }
            }
          >
            {canGenerate && (
              <div
                className="absolute inset-0 opacity-25"
                style={{
                  background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent)',
                  animation: 'shimmer 2.5s ease-in-out infinite',
                }}
              />
            )}
            <span className="relative flex items-center justify-center gap-2.5">
              <Zap className="w-4 h-4" />
              {canGenerate ? 'View Player Pool & Generate XI →' : 'Select both teams to continue'}
            </span>
          </motion.button>
        </motion.div>

        {/* Footer */}
        <motion.p variants={item} className="text-slate-600 text-xs tracking-widest uppercase font-medium text-center pb-4">
          Powered by Elo · HMM · Genetic Algorithm
        </motion.p>
      </motion.div>

      <style>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(200%); }
        }
      `}</style>
    </div>
  )
}
