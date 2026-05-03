import { useState } from 'react'
import { motion } from 'framer-motion'
import { Flame, Snowflake, Minus, TrendingUp } from 'lucide-react'
import type { PlayerProfile } from '@/types'
import { cn, fmt, roleBadgeColor, roleShort } from '@/lib/utils'

interface PlayerCardProps {
  player: PlayerProfile
  teamColor: string
  teamColorSecondary?: string
  onBench: () => void
  onReinstate: () => void
}

function FormBadge({ form }: { form: PlayerProfile['form_state'] }) {
  if (form === 'hot') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-orange-500/20 text-orange-300 border border-orange-500/30 animate-pulse">
        <Flame className="w-3 h-3" />
        HOT
      </span>
    )
  }
  if (form === 'cold') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
        <Snowflake className="w-3 h-3" />
        COLD
      </span>
    )
  }
  if (form === 'avg') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-sky-500/20 text-sky-300 border border-sky-500/30">
        <Minus className="w-3 h-3" />
        AVG
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-slate-700/30 text-slate-500 border border-slate-700/30">
      ?
    </span>
  )
}

function EloBar({ multiplier }: { multiplier: number }) {
  const isPositive = multiplier >= 1
  const deviation = Math.abs(multiplier - 1)
  const barWidth = Math.min(deviation * 200, 100)
  const color = isPositive ? '#22c55e' : '#ef4444'

  return (
    <div className="flex items-center gap-2 mt-1">
      <span className="text-xs font-mono text-slate-500 w-16 shrink-0">
        ELO{' '}
        <span style={{ color }} className="font-bold">
          ×{multiplier.toFixed(2)}
        </span>
      </span>
      <div className="flex-1 h-1 rounded-full bg-white/[0.06] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${barWidth}%`,
            background: `linear-gradient(90deg, ${color}88, ${color})`,
          }}
        />
      </div>
    </div>
  )
}

function Avatar({
  photoUrl,
  name,
  teamColor,
}: {
  photoUrl: string | null
  name: string
  teamColor: string
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
      className="relative shrink-0 w-14 h-14 rounded-full overflow-hidden"
      style={{ boxShadow: `0 0 0 3px ${teamColor}60` }}
    >
      {/* Initials fallback — always rendered beneath the photo */}
      <div
        className="absolute inset-0 flex items-center justify-center text-sm font-bold text-white"
        style={{ background: `linear-gradient(135deg, ${teamColor}60, ${teamColor}30)` }}
      >
        {initials}
      </div>

      {photoUrl && (
        <>
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
          {/* Subtle gradient overlay at bottom for blending */}
          {loaded && (
            <div
              className="absolute bottom-0 left-0 right-0 h-2 pointer-events-none"
              style={{ background: `linear-gradient(to top, ${teamColor}40, transparent)` }}
            />
          )}
        </>
      )}
    </div>
  )
}

export default function PlayerCard({
  player,
  teamColor,
  onBench,
  onReinstate,
}: PlayerCardProps) {
  const isBenched = !player.is_active
  const adjScore =
    player.adjusted_score != null
      ? player.adjusted_score
      : player.rolling_avg != null
      ? player.rolling_avg * player.elo_multiplier
      : null

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16, scale: 0.97 }}
      animate={{ opacity: isBenched ? 0.5 : 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      whileHover={{ scale: 1.02, y: -2 }}
      transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
      className="relative group rounded-xl overflow-hidden border border-white/[0.08] bg-white/[0.04] backdrop-blur-md"
      style={{ boxShadow: isBenched ? 'none' : `0 2px 24px ${teamColor}18` }}
    >
      {/* Left accent bar */}
      <div
        className="absolute left-0 top-0 bottom-0 w-[3px]"
        style={{ background: `linear-gradient(to bottom, ${teamColor}, ${teamColor}66)` }}
      />

      {/* Benched overlay badge */}
      {isBenched && (
        <div className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none">
          <span className="px-3 py-1 rounded-full text-xs font-black tracking-widest bg-black/70 text-slate-400 border border-white/10 uppercase">
            Benched
          </span>
        </div>
      )}

      {/* Bench / reinstate button — top right */}
      <div className="absolute top-2 right-2 z-20">
        {isBenched ? (
          <button
            onClick={onReinstate}
            className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30 transition-colors"
          >
            Reinstate
          </button>
        ) : (
          <button
            onClick={onBench}
            className="px-2 py-0.5 rounded text-xs font-semibold bg-white/[0.04] text-slate-500 border border-white/[0.08] opacity-0 group-hover:opacity-100 hover:bg-red-500/20 hover:text-red-400 hover:border-red-500/30 transition-all duration-150"
          >
            Bench
          </button>
        )}
      </div>

      <div className="pl-4 pr-3 pt-3 pb-3">
        {/* Top row: avatar + name + role */}
        <div className="flex items-start gap-3">
          <Avatar photoUrl={player.photo_url} name={player.player_name} teamColor={teamColor} />

          <div className="flex-1 min-w-0 mt-0.5">
            <p className="text-sm font-semibold text-white leading-tight truncate pr-12">
              <span className="text-xs font-semibold text-slate-500 mr-2">
                Elo {fmt(player.elo_post, 0)}
              </span>
              {player.player_name}
            </p>
            <div className="flex items-center gap-1.5 mt-1 flex-wrap">
              <span
                className={cn(
                  'inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold border',
                  roleBadgeColor(player.role)
                )}
              >
                {roleShort(player.role)}
              </span>
              <FormBadge form={player.form_state} />
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="mt-3 grid grid-cols-2 gap-2">
          <div className="rounded-lg bg-white/[0.04] px-2.5 py-2 border border-white/[0.05]">
            <p className="text-slate-500 text-xs mb-0.5">Credits</p>
            <p className="text-white font-bold text-lg leading-none">{player.credits.toFixed(1)}</p>
          </div>
          <div className="rounded-lg bg-white/[0.04] px-2.5 py-2 border border-white/[0.05]">
            <p className="text-slate-500 text-xs mb-0.5 flex items-center gap-1">
              <TrendingUp className="w-3 h-3" />
              Adj. Score
            </p>
            <p
              className="font-bold text-lg leading-none"
              style={{ color: adjScore != null ? teamColor : undefined }}
            >
              {fmt(adjScore)}
            </p>
          </div>
        </div>

        {/* ELO bar */}
        <EloBar multiplier={player.elo_multiplier} />

        {/* Rolling avg note */}
        {player.rolling_avg != null && (
          <p className="text-xs text-slate-600 mt-1.5">
            Rolling avg: <span className="text-slate-400">{fmt(player.rolling_avg)}</span>
            {player.rolling_window > 0 && (
              <span className="ml-1 text-slate-600">({player.rolling_window} matches)</span>
            )}
          </p>
        )}
      </div>
    </motion.div>
  )
}
