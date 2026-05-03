import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Trophy, Users, RefreshCw, Shield, Zap, Scale } from 'lucide-react'
import type { GenerateResult, TeamPlayer } from '@/types'
import { getFranchise } from '@/constants/franchises'
import { cn, fmt, roleBadgeColor, roleShort } from '@/lib/utils'
import TeamColumn from './TeamColumn'

interface WarRoomProps {
  result: GenerateResult
}

function SharedPlayerBadge({
  player,
  inCount,
}: {
  player: TeamPlayer
  inCount: number
}) {
  const franchise = getFranchise(player.team)
  const isCore = inCount === 3

  return (
    <div
      className={cn(
        'flex items-center gap-2 px-3 py-2 rounded-xl border transition-all',
        isCore
          ? 'bg-white/[0.07] border-white/[0.15]'
          : 'bg-white/[0.03] border-white/[0.07]'
      )}
      style={
        isCore
          ? {
              boxShadow: `0 0 12px ${franchise.primary}20`,
            }
          : {}
      }
    >
      {/* Team dot */}
      <div
        className="w-2.5 h-2.5 rounded-full flex-shrink-0"
        style={{ background: franchise.primary }}
      />
      {/* Name */}
      <p
        className={cn(
          'text-sm font-semibold truncate flex-1',
          isCore ? 'text-white' : 'text-slate-300'
        )}
      >
        <span className="text-xs font-semibold text-slate-500 mr-2">
          Elo {fmt(player.elo_post, 0)}
        </span>
        {player.player_name}
      </p>
      {/* Role */}
      <span
        className={cn(
          'text-xs font-bold px-1.5 py-0.5 rounded border flex-shrink-0',
          roleBadgeColor(player.role)
        )}
      >
        {roleShort(player.role)}
      </span>
      {/* Count indicator */}
      <div
        className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-black flex-shrink-0"
        style={
          isCore
            ? {
                background: 'linear-gradient(135deg, #eab308, #f59e0b)',
                color: '#000',
              }
            : {
                background: 'rgba(255,255,255,0.08)',
                color: '#94a3b8',
              }
        }
      >
        {inCount}
      </div>
    </div>
  )
}

type MobileTab = 'safe' | 'balanced' | 'explosive'

const MOBILE_TABS: { id: MobileTab; label: string; icon: typeof Shield }[] = [
  { id: 'safe', label: 'Safe', icon: Shield },
  { id: 'balanced', label: 'Balanced', icon: Scale },
  { id: 'explosive', label: 'Explosive', icon: Zap },
]

export default function WarRoom({ result }: WarRoomProps) {
  const navigate = useNavigate()
  const [mobileTab, setMobileTab] = useState<MobileTab>('balanced')
  const franchiseA = getFranchise(result.match.team_a)
  const franchiseB = getFranchise(result.match.team_b)

  // Compute shared players across strategies
  const { corePicks, twoOfThree } = useMemo(() => {
    const allStrategies = [result.safe.players, result.explosive.players, result.balanced.players]

    const countMap = new Map<string, { player: TeamPlayer; count: number }>()
    for (const stratPlayers of allStrategies) {
      for (const p of stratPlayers) {
        const existing = countMap.get(p.player_id)
        if (existing) {
          existing.count++
        } else {
          countMap.set(p.player_id, { player: p, count: 1 })
        }
      }
    }

    const core: TeamPlayer[] = []
    const two: TeamPlayer[] = []
    for (const { player, count } of countMap.values()) {
      if (count === 3) core.push(player)
      else if (count === 2) two.push(player)
    }

    // Sort by credits descending
    core.sort((a, b) => b.credits - a.credits)
    two.sort((a, b) => b.credits - a.credits)

    return { corePicks: core, twoOfThree: two }
  }, [result])

  return (
    <div
      className="min-h-screen relative overflow-x-hidden"
      style={{ background: '#0a0a0f' }}
    >
      {/* Background gradient bleed from team colors */}
      <div
        className="pointer-events-none fixed inset-0"
        style={{
          background: `
            radial-gradient(ellipse 60% 40% at 0% 0%, ${franchiseA.primary}0D 0%, transparent 50%),
            radial-gradient(ellipse 60% 40% at 100% 0%, ${franchiseB.primary}0D 0%, transparent 50%),
            radial-gradient(ellipse 80% 50% at 50% 100%, rgba(99,102,241,0.05) 0%, transparent 60%)
          `,
        }}
      />

      <div className="relative z-10 max-w-screen-2xl mx-auto px-4 sm:px-6 py-8 flex flex-col gap-10">
        {/* Page heading */}
        <motion.div
          initial={{ opacity: 0, y: -24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center flex flex-col items-center gap-4"
        >
          {/* Trophy icon */}
          <div
            className="w-14 h-14 rounded-2xl flex items-center justify-center"
            style={{
              background: 'linear-gradient(135deg, #eab30820, #f59e0b15)',
              border: '1px solid #eab30830',
              boxShadow: '0 0 32px #eab30820',
            }}
          >
            <Trophy className="w-7 h-7 text-yellow-400" />
          </div>

          <div>
            <h1
              className="text-4xl sm:text-5xl font-black tracking-tighter text-white"
              style={{ textShadow: '0 0 40px rgba(255,255,255,0.1)' }}
            >
              WAR ROOM
            </h1>
            <p className="text-slate-500 text-sm mt-1 tracking-wide">
              Your AI-generated fantasy squads — choose your strategy
            </p>
          </div>

          {/* Match banner */}
          <div className="flex items-center gap-3 px-5 py-2.5 rounded-2xl bg-white/[0.05] border border-white/[0.08]">
            <div className="flex items-center gap-2">
              <span
                className="w-3 h-3 rounded-full"
                style={{
                  background: franchiseA.primary,
                  boxShadow: `0 0 8px ${franchiseA.primary}`,
                }}
              />
              <span className="text-sm font-bold text-white">{franchiseA.emoji} {result.match.team_a}</span>
            </div>
            <span className="text-xs font-black tracking-widest text-slate-500 px-2">VS</span>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-white">{franchiseB.emoji} {result.match.team_b}</span>
              <span
                className="w-3 h-3 rounded-full"
                style={{
                  background: franchiseB.primary,
                  boxShadow: `0 0 8px ${franchiseB.primary}`,
                }}
              />
            </div>
          </div>
        </motion.div>

        {/* Mobile tab bar (hidden on md+) */}
        <div className="flex md:hidden rounded-2xl overflow-hidden border border-white/[0.08] bg-white/[0.02]">
          {MOBILE_TABS.map(tab => {
            const Icon = tab.icon
            const active = mobileTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setMobileTab(tab.id)}
                className="flex-1 flex items-center justify-center gap-1.5 py-3 text-sm font-bold transition-all"
                style={
                  active
                    ? { background: 'rgba(255,255,255,0.08)', color: '#fff' }
                    : { color: '#64748b' }
                }
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            )
          })}
        </div>

        {/* Mobile: single active column */}
        <div className="md:hidden">
          <motion.div
            key={mobileTab}
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          >
            <TeamColumn result={result[mobileTab]} rank={mobileTab === 'safe' ? 1 : mobileTab === 'balanced' ? 2 : 3} />
          </motion.div>
        </div>

        {/* Desktop: three columns — balanced in center is featured */}
        <div className="hidden md:grid md:grid-cols-3 gap-4 items-start">
          {/* Safe */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.1 }}
            className="h-full"
          >
            <TeamColumn result={result.safe} rank={1} />
          </motion.div>

          {/* Balanced — center, slightly elevated/larger */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.2 }}
            className="h-full md:-mt-3"
            style={{ transform: 'scale(1.02)', transformOrigin: 'top center' }}
          >
            <TeamColumn result={result.balanced} rank={2} />
          </motion.div>

          {/* Explosive */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.3 }}
            className="h-full"
          >
            <TeamColumn result={result.explosive} rank={3} />
          </motion.div>
        </div>

        {/* Shared Players section */}
        {(corePicks.length > 0 || twoOfThree.length > 0) && (
          <motion.div
            initial={{ opacity: 0, y: 32 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.5 }}
            className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-6"
          >
            <div className="flex items-center gap-3 mb-5">
              <div className="w-9 h-9 rounded-xl bg-yellow-500/10 border border-yellow-500/20 flex items-center justify-center">
                <Users className="w-4 h-4 text-yellow-400" />
              </div>
              <div>
                <h2 className="text-base font-black text-white">Shared Players</h2>
                <p className="text-xs text-slate-500">Players appearing in multiple strategies</p>
              </div>
            </div>

            {corePicks.length > 0 && (
              <div className="mb-5">
                <div className="flex items-center gap-2 mb-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-yellow-400" />
                  <p className="text-xs font-bold uppercase tracking-widest text-yellow-400">
                    Core Picks · All 3 Teams
                  </p>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                  {corePicks.map(p => (
                    <SharedPlayerBadge key={p.player_id} player={p} inCount={3} />
                  ))}
                </div>
              </div>
            )}

            {twoOfThree.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                  <p className="text-xs font-bold uppercase tracking-widest text-slate-400">
                    Suggested · 2 of 3 Teams
                  </p>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                  {twoOfThree.map(p => (
                    <SharedPlayerBadge key={p.player_id} player={p} inCount={2} />
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* Footer actions */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.7 }}
          className="flex justify-center pb-8"
        >
          <button
            onClick={() => navigate('/')}
            className={cn(
              'flex items-center gap-2.5 px-8 py-3.5 rounded-2xl font-bold text-sm',
              'border border-white/[0.10] bg-white/[0.04] text-slate-300',
              'hover:bg-white/[0.08] hover:text-white hover:border-white/20 transition-all duration-200'
            )}
          >
            <RefreshCw className="w-4 h-4" />
            New Match
          </button>
        </motion.div>
      </div>
    </div>
  )
}
