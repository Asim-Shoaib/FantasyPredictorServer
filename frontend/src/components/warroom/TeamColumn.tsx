import { useState } from 'react'
import { motion } from 'framer-motion'
import { Shield, Zap, Scale, TrendingUp, Star, Award } from 'lucide-react'
import type { TeamResult, TeamPlayer } from '@/types'
import { getFranchise } from '@/constants/franchises'
import { cn, fmt, roleBadgeColor, roleShort } from '@/lib/utils'

interface TeamColumnProps {
  result: TeamResult
  rank?: number
}

const STRATEGY_META = {
  safe: {
    label: 'SAFE',
    icon: Shield,
    color: '#3b82f6',
    colorDim: '#3b82f620',
    borderColor: '#3b82f650',
    gradient: 'linear-gradient(135deg, #1d4ed8, #3b82f6)',
  },
  explosive: {
    label: 'EXPLOSIVE',
    icon: Zap,
    color: '#f97316',
    colorDim: '#f9731620',
    borderColor: '#f9731650',
    gradient: 'linear-gradient(135deg, #c2410c, #f97316)',
  },
  balanced: {
    label: 'BALANCED',
    icon: Scale,
    color: '#a855f7',
    colorDim: '#a855f720',
    borderColor: '#a855f750',
    gradient: 'linear-gradient(135deg, #7e22ce, #a855f7)',
  },
}

function FormDot({ form }: { form: TeamPlayer['form_state'] }) {
  if (form === 'hot')
    return (
      <span
        className="w-2 h-2 rounded-full flex-shrink-0 animate-pulse"
        style={{ background: '#f97316', boxShadow: '0 0 4px #f97316' }}
      />
    )
  if (form === 'cold')
    return (
      <span
        className="w-2 h-2 rounded-full flex-shrink-0"
        style={{ background: '#22d3ee' }}
      />
    )
  if (form === 'avg')
    return (
      <span
        className="w-2 h-2 rounded-full flex-shrink-0"
        style={{ background: '#38bdf8', boxShadow: '0 0 4px #38bdf8' }}
      />
    )
  return <span className="w-2 h-2 rounded-full flex-shrink-0 bg-slate-700" />
}

function MiniAvatar({
  photoUrl,
  name,
  franchiseColor,
}: {
  photoUrl: string | null
  name: string
  franchiseColor: string
}) {
  const [loaded, setLoaded] = useState(false)

  const initials = name
    .split(' ')
    .map(w => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  return (
    <div
      className="relative w-8 h-8 rounded-full overflow-hidden flex-shrink-0"
      style={{ boxShadow: `0 0 0 1.5px ${franchiseColor}60` }}
    >
      {/* Initials fallback */}
      <div
        className="absolute inset-0 flex items-center justify-center text-xs font-bold text-white"
        style={{ background: `linear-gradient(135deg, ${franchiseColor}60, ${franchiseColor}30)` }}
      >
        {initials}
      </div>

      {photoUrl && (
        <img
          src={photoUrl}
          alt={name}
          className="absolute inset-0 w-full h-full object-cover object-top transition-opacity duration-500"
          style={{ opacity: loaded ? 1 : 0 }}
          onLoad={() => setLoaded(true)}
          onError={e => {
            ;(e.target as HTMLImageElement).style.display = 'none'
          }}
        />
      )}
    </div>
  )
}

function CaptainCard({
  player,
  type,
}: {
  player: TeamPlayer
  type: 'captain' | 'vc'
}) {
  const franchise = getFranchise(player.team)
  const borderColor = type === 'captain' ? '#eab308' : '#94a3b8'
  const bgColor = type === 'captain' ? '#eab30812' : '#94a3b810'
  const labelColor = type === 'captain' ? '#eab308' : '#94a3b8'

  return (
    <div
      className="rounded-xl p-3 flex items-center gap-3"
      style={{
        background: bgColor,
        border: `1px solid ${borderColor}30`,
        boxShadow: `0 0 12px ${borderColor}10`,
      }}
    >
      {/* Badge */}
      <div
        className="w-9 h-9 rounded-full flex items-center justify-center font-black text-xs flex-shrink-0"
        style={{
          background: `linear-gradient(135deg, ${borderColor}30, ${borderColor}15)`,
          border: `1.5px solid ${borderColor}50`,
          color: labelColor,
        }}
      >
        {type === 'captain' ? 'C' : 'VC'}
      </div>

      {/* Photo avatar */}
      <MiniAvatar
        photoUrl={player.photo_url ?? null}
        name={player.player_name}
        franchiseColor={franchise.primary}
      />

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-xs font-semibold text-slate-500 shrink-0">
            Elo {fmt(player.elo_post, 0)}
          </span>
          <p className="text-sm font-bold text-white truncate">{player.player_name}</p>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          <span
            className={cn(
              'inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold border',
              roleBadgeColor(player.role)
            )}
          >
            {roleShort(player.role)}
          </span>
          <span className="text-xs text-slate-500">{franchise.shortName}</span>
          <FormDot form={player.form_state} />
        </div>
      </div>

      {/* Credits */}
      <div className="text-right shrink-0">
        <p className="text-sm font-black text-white">{player.credits.toFixed(1)}</p>
        <p className="text-xs text-slate-500">cr</p>
      </div>
    </div>
  )
}

function PlayerRow({
  player,
  index,
  isCaptain,
  isVc,
}: {
  player: TeamPlayer
  index: number
  isCaptain: boolean
  isVc: boolean
}) {
  const franchise = getFranchise(player.team)

  return (
    <div
      className={cn(
        'flex items-center gap-2 px-3 py-2 rounded-lg transition-colors',
        (isCaptain || isVc) ? 'bg-white/[0.06]' : index % 2 === 0 ? 'bg-white/[0.02]' : ''
      )}
    >
      {/* Number */}
      <span className="text-xs font-bold text-slate-600 w-5 shrink-0 tabular-nums">
        {index + 1}
      </span>

      {/* Form dot */}
      <FormDot form={player.form_state} />

      {/* Name */}
      <p
        className={cn(
          'flex-1 text-sm font-medium truncate',
          isCaptain || isVc ? 'text-white font-bold' : 'text-slate-300'
        )}
      >
        <span className="text-xs font-semibold text-slate-500 mr-2">
          Elo {fmt(player.elo_post, 0)}
        </span>
        {player.player_name}
      </p>

      {/* Captain / VC indicator */}
      {(isCaptain || isVc) && (
        <span
          className="text-xs font-black px-1 rounded"
          style={{
            color: isCaptain ? '#eab308' : '#94a3b8',
            background: isCaptain ? '#eab30820' : '#94a3b815',
          }}
        >
          {isCaptain ? 'C' : 'VC'}
        </span>
      )}

      {/* Role */}
      <span
        className={cn(
          'text-xs font-bold px-1.5 py-0.5 rounded border',
          roleBadgeColor(player.role)
        )}
      >
        {roleShort(player.role)}
      </span>

      {/* Credits */}
      <span
        className="text-xs font-bold shrink-0 w-8 text-right"
        style={{ color: franchise.secondary }}
      >
        {player.credits.toFixed(1)}
      </span>
    </div>
  )
}

function TeamCompositionBar({ players }: { players: TeamPlayer[] }) {
  const counts: Record<string, { count: number; franchise: ReturnType<typeof getFranchise> }> = {}
  for (const p of players) {
    if (!counts[p.team]) counts[p.team] = { count: 0, franchise: getFranchise(p.team) }
    counts[p.team].count++
  }

  return (
    <div className="mt-3 pt-3 border-t border-white/[0.06]">
      <p className="text-xs text-slate-600 uppercase tracking-wider font-semibold mb-2">
        Composition
      </p>
      <div className="flex gap-2 flex-wrap">
        {Object.entries(counts).map(([team, { count, franchise }]) => (
          <div
            key={team}
            className="flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-bold"
            style={{
              background: franchise.primary + '20',
              border: `1px solid ${franchise.primary}30`,
              color: franchise.secondary,
            }}
          >
            <span
              className="w-2 h-2 rounded-full"
              style={{ background: franchise.primary }}
            />
            <span className="text-white/80">{franchise.shortName}</span>
            <span>{count}</span>
          </div>
        ))}
      </div>

      {/* Composition bar */}
      <div className="h-2 rounded-full overflow-hidden flex mt-2 gap-px">
        {Object.entries(counts).map(([team, { count, franchise }]) => (
          <div
            key={team}
            className="h-full transition-all duration-700"
            style={{
              width: `${(count / players.length) * 100}%`,
              background: franchise.primary,
            }}
          />
        ))}
      </div>
    </div>
  )
}

function roleSortKey(role: string): number {
  const r = role.toLowerCase()
  if (r.includes('wicket') || r === 'wk' || r === 'wk-batter') return 0
  if (r.includes('bat')) return 1
  if (r.includes('all')) return 2
  if (r.includes('bowl')) return 3
  return 4
}

export default function TeamColumn({ result, rank }: TeamColumnProps) {
  const meta = STRATEGY_META[result.strategy]
  const Icon = meta.icon
  const sortedPlayers = [...result.players].sort((a, b) => {
    const order = roleSortKey(a.role) - roleSortKey(b.role)
    if (order !== 0) return order
    return a.player_name.localeCompare(b.player_name)
  })

  return (
    <div
      className={cn(
        'relative flex flex-col rounded-2xl overflow-hidden border h-full',
        'bg-white/[0.03]'
      )}
      style={{ borderColor: meta.borderColor }}
    >
      {/* Top colored accent bar */}
      <div className="h-1 w-full" style={{ background: meta.gradient }} />

      {/* Header */}
      <div
        className="px-4 pt-4 pb-3 flex items-center gap-3"
        style={{ borderBottom: `1px solid ${meta.color}15` }}
      >
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ background: meta.colorDim, border: `1px solid ${meta.borderColor}` }}
        >
          <Icon className="w-5 h-5" style={{ color: meta.color }} />
        </div>
        <div className="flex-1">
          <p
            className="text-base font-black tracking-wider"
            style={{ color: meta.color }}
          >
            {meta.label}
          </p>
          {rank !== undefined && (
            <p className="text-xs text-slate-500">Strategy #{rank}</p>
          )}
        </div>
        {result.strategy === 'balanced' && (
          <div
            className="px-2 py-0.5 rounded-full text-xs font-bold"
            style={{
              background: meta.colorDim,
              color: meta.color,
              border: `1px solid ${meta.borderColor}`,
            }}
          >
            FEATURED
          </div>
        )}
      </div>

      {/* Stats row */}
      <div className="px-4 py-3 grid grid-cols-2 gap-2" style={{ borderBottom: `1px solid ${meta.color}10` }}>
        <div className="rounded-xl bg-white/[0.04] px-3 py-2.5">
          <div className="flex items-center gap-1.5 mb-1">
            <Award className="w-3 h-3 text-slate-500" />
            <p className="text-xs text-slate-500">Expected</p>
          </div>
          <p className="text-sm font-black text-white">
            {fmt(result.expected_score, 1)}
          </p>
        </div>
        <div className="rounded-xl bg-white/[0.04] px-3 py-2.5">
          <div className="flex items-center gap-1.5 mb-1">
            <TrendingUp className="w-3 h-3 text-slate-500" />
            <p className="text-xs text-slate-500">Ceiling</p>
          </div>
          <p className="text-sm font-black" style={{ color: meta.color }}>
            {fmt(result.ceiling_score, 1)}
          </p>
        </div>
        <div className="rounded-xl bg-white/[0.04] px-3 py-2.5 col-span-2">
          <div className="flex items-center gap-1.5 mb-1">
            <Shield className="w-3 h-3 text-slate-500" />
            <p className="text-xs text-slate-500">Floor</p>
          </div>
          <p className="text-sm font-black text-white">
            {fmt(result.floor_score, 1)}
          </p>
        </div>
      </div>

      {/* Captain section */}
      <div className="px-4 pt-3 pb-2 flex flex-col gap-2">
        <div className="flex items-center gap-2 mb-1">
          <Star className="w-3 h-3 text-yellow-500" />
          <p className="text-xs font-bold uppercase tracking-widest text-slate-500">
            Key Picks
          </p>
        </div>
        <CaptainCard player={result.captain} type="captain" />
        <CaptainCard player={result.vc} type="vc" />
      </div>

      {/* Player list */}
      <div
        className="flex-1 px-4 py-2 flex flex-col gap-0.5"
        style={{ borderTop: `1px solid ${meta.color}10` }}
      >
        <p className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-1 py-1">
          Full XI
        </p>
        {sortedPlayers.map((player, i) => (
          <PlayerRow
            key={player.player_id}
            player={player}
            index={i}
            isCaptain={player.player_id === result.captain.player_id}
            isVc={player.player_id === result.vc.player_id}
          />
        ))}
      </div>

      {/* Team composition at bottom */}
      <div className="px-4 pb-4">
        <TeamCompositionBar players={result.players} />
      </div>
    </div>
  )
}
