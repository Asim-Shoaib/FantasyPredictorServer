import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search } from 'lucide-react'
import type { PlayerProfile } from '@/types'
import { getFranchise } from '@/constants/franchises'
import { cn } from '@/lib/utils'
import PlayerCard from './PlayerCard'

interface PlayerPoolProps {
  players: PlayerProfile[]
  teamA: string
  teamB: string
  onBench: (id: string) => void
  onReinstate: (id: string) => void
  loading: boolean
}

type RoleFilter = 'all' | 'wk' | 'bat' | 'ar' | 'bowl'
type TeamFilter = 'all' | 'a' | 'b'
type SortKey = 'credits' | 'form' | 'score'

const ROLE_TABS: { key: RoleFilter; label: string }[] = [
  { key: 'all', label: 'ALL' },
  { key: 'wk', label: 'WK' },
  { key: 'bat', label: 'BAT' },
  { key: 'ar', label: 'AR' },
  { key: 'bowl', label: 'BWL' },
]

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: 'credits', label: 'Credits' },
  { key: 'form', label: 'Form' },
  { key: 'score', label: 'Score' },
]

function roleMatchesFilter(role: string, filter: RoleFilter): boolean {
  if (filter === 'all') return true
  const r = role.toLowerCase()
  if (filter === 'wk') return r.includes('wicket') || r === 'wk' || r === 'wk-batter'
  if (filter === 'bat') return r.includes('bat') && !r.includes('wicket') && !r.includes('all')
  if (filter === 'ar') return r.includes('all')
  if (filter === 'bowl') return r.includes('bowl')
  return true
}

const FORM_ORDER: Record<string, number> = { hot: 0, avg: 1, cold: 2, unknown: 3 }

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] overflow-hidden animate-pulse">
      <div className="pl-4 pr-3 pt-3 pb-3">
        <div className="flex items-start gap-3">
          <div className="w-11 h-11 rounded-full bg-white/[0.06]" />
          <div className="flex-1 mt-0.5">
            <div className="h-3.5 bg-white/[0.06] rounded w-3/4 mb-2" />
            <div className="h-3 bg-white/[0.04] rounded w-1/2" />
          </div>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2">
          <div className="h-14 rounded-lg bg-white/[0.04]" />
          <div className="h-14 rounded-lg bg-white/[0.04]" />
        </div>
        <div className="mt-2 h-3 bg-white/[0.04] rounded w-full" />
      </div>
    </div>
  )
}

export default function PlayerPool({
  players,
  teamA,
  teamB,
  onBench,
  onReinstate,
  loading,
}: PlayerPoolProps) {
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('all')
  const [teamFilter, setTeamFilter] = useState<TeamFilter>('all')
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('credits')

  const franchiseA = getFranchise(teamA)
  const franchiseB = getFranchise(teamB)

  const filtered = useMemo(() => {
    let result = [...players]

    if (teamFilter === 'a') result = result.filter(p => p.team === teamA)
    else if (teamFilter === 'b') result = result.filter(p => p.team === teamB)

    if (roleFilter !== 'all') {
      result = result.filter(p => roleMatchesFilter(p.role, roleFilter))
    }

    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(p => p.player_name.toLowerCase().includes(q))
    }

    result.sort((a, b) => {
      // Active before benched
      if (a.is_active !== b.is_active) return a.is_active ? -1 : 1

      if (sortKey === 'credits') return b.credits - a.credits
      if (sortKey === 'form') return (FORM_ORDER[a.form_state] ?? 3) - (FORM_ORDER[b.form_state] ?? 3)
      if (sortKey === 'score') {
        const sa = a.adjusted_score ?? (a.rolling_avg != null ? a.rolling_avg * a.elo_multiplier : 0)
        const sb = b.adjusted_score ?? (b.rolling_avg != null ? b.rolling_avg * b.elo_multiplier : 0)
        return sb - sa
      }
      return 0
    })

    return result
  }, [players, teamFilter, roleFilter, search, sortKey, teamA, teamB])

  const activeCount = players.filter(p => p.is_active).length

  const teamAFilterLabel = franchiseA.shortName
  const teamBFilterLabel = franchiseB.shortName

  return (
    <div className="flex flex-col gap-4">
      {/* Filters row */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:flex-wrap">
        {/* Role tabs */}
        <div className="flex items-center gap-1 rounded-xl bg-white/[0.04] p-1 border border-white/[0.06]">
          {ROLE_TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setRoleFilter(tab.key)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-bold tracking-wide transition-all duration-150',
                roleFilter === tab.key
                  ? 'bg-white/[0.12] text-white shadow'
                  : 'text-slate-500 hover:text-slate-300'
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Team filter */}
        <div className="flex items-center gap-1 rounded-xl bg-white/[0.04] p-1 border border-white/[0.06]">
          {[
            { key: 'all' as TeamFilter, label: 'BOTH', color: undefined },
            { key: 'a' as TeamFilter, label: teamAFilterLabel, color: franchiseA.primary },
            { key: 'b' as TeamFilter, label: teamBFilterLabel, color: franchiseB.primary },
          ].map(item => (
            <button
              key={item.key}
              onClick={() => setTeamFilter(item.key)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-bold tracking-wide transition-all duration-150',
                teamFilter === item.key ? 'text-white shadow' : 'text-slate-500 hover:text-slate-300'
              )}
              style={
                teamFilter === item.key && item.color
                  ? { background: item.color + '40', boxShadow: `0 0 0 1px ${item.color}60` }
                  : teamFilter === item.key
                  ? { background: 'rgba(255,255,255,0.12)' }
                  : {}
              }
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Sort */}
        <div className="flex items-center gap-1 rounded-xl bg-white/[0.04] p-1 border border-white/[0.06]">
          {SORT_OPTIONS.map(opt => (
            <button
              key={opt.key}
              onClick={() => setSortKey(opt.key)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-bold tracking-wide transition-all duration-150',
                sortKey === opt.key
                  ? 'bg-white/[0.12] text-white shadow'
                  : 'text-slate-500 hover:text-slate-300'
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative flex-1 min-w-[180px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search player…"
            className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl pl-9 pr-4 py-2 text-sm text-white placeholder:text-slate-600 outline-none focus:border-white/20 transition-colors"
          />
        </div>
      </div>

      {/* Count */}
      <p className="text-xs text-slate-500">
        Showing <span className="text-slate-300 font-semibold">{filtered.length}</span> players
        <span className="ml-1 text-slate-600">
          ({activeCount} active)
        </span>
      </p>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          {Array.from({ length: 10 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-20 text-slate-600"
        >
          <p className="text-4xl mb-3">🏏</p>
          <p className="text-sm">No players match your filters</p>
        </motion.div>
      ) : (
        <motion.div
          layout
          className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3"
        >
          <AnimatePresence mode="popLayout">
            {filtered.map(player => {
              const isTeamA = player.team === teamA
              const franchise = isTeamA ? franchiseA : franchiseB
              return (
                <PlayerCard
                  key={player.player_id}
                  player={player}
                  teamColor={franchise.primary}
                  teamColorSecondary={franchise.secondary}
                  onBench={() => onBench(player.player_id)}
                  onReinstate={() => onReinstate(player.player_id)}
                />
              )
            })}
          </AnimatePresence>
        </motion.div>
      )}
    </div>
  )
}
