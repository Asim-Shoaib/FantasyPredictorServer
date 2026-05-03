import { useState } from 'react'
import { motion } from 'framer-motion'
import { Flame, Snowflake, Minus } from 'lucide-react'
import type { PlayerProfile } from '@/types'
import { cn, fmt, roleShort } from '@/lib/utils'

interface PlayerCardProps {
  player: PlayerProfile
  teamColor: string
  teamColorSecondary?: string
  onBench: () => void
  onReinstate: () => void
}

function getRoleColor(role: string): string {
  const r = role.toLowerCase()
  if (r.includes('wicket') || r === 'wk' || r === 'wk-batter') return '#ec4899'
  if (r.includes('bat') && !r.includes('all')) return '#3b82f6'
  if (r.includes('all')) return '#8b5cf6'
  if (r.includes('bowl')) return '#f59e0b'
  return '#64748b'
}

function FormBadge({ form }: { form: PlayerProfile['form_state'] }) {
  if (form === 'hot') {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-orange-500/15 text-orange-300 border border-orange-500/25 animate-pulse">
        <Flame className="w-2.5 h-2.5" />
        HOT
      </span>
    )
  }
  if (form === 'cold') {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-cyan-500/15 text-cyan-300 border border-cyan-500/25">
        <Snowflake className="w-2.5 h-2.5" />
        COLD
      </span>
    )
  }
  if (form === 'avg') {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-700/30 text-slate-400 border border-slate-700/30">
        <Minus className="w-2.5 h-2.5" />
        AVG
      </span>
    )
  }
  return (
    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-800/50 text-slate-600 border border-slate-700/20">
      —
    </span>
  )
}

function Avatar({ photoUrl, name, roleColor }: { photoUrl: string | null; name: string; roleColor: string }) {
  const [loaded, setLoaded] = useState(false)

  const initials = name
    .split(' ')
    .map(w => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  return (
    <div
      className="relative shrink-0 w-12 h-12 rounded-full overflow-hidden"
      style={{ boxShadow: `0 0 0 2px ${roleColor}60` }}
    >
      <div
        className="absolute inset-0 flex items-center justify-center text-xs font-bold text-white"
        style={{ background: `linear-gradient(135deg, ${roleColor}50, ${roleColor}25)` }}
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
          onError={e => { ;(e.target as HTMLImageElement).style.display = 'none' }}
        />
      )}
    </div>
  )
}

function EloBar({ multiplier, roleColor }: { multiplier: number; roleColor: string }) {
  const deviation = Math.abs(multiplier - 1)
  const barWidth = Math.min(deviation * 200, 100)

  return (
    <div className="flex items-center gap-2 mt-2">
      <span className="text-[10px] font-mono text-slate-500 shrink-0">
        ELO{' '}
        <span className="font-bold" style={{ color: roleColor }}>
          ×{multiplier.toFixed(2)}
        </span>
      </span>
      <div className="flex-1 h-[3px] rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${barWidth}%`,
            background: `linear-gradient(90deg, ${roleColor}66, ${roleColor})`,
          }}
        />
      </div>
    </div>
  )
}

export default function PlayerCard({ player, onBench, onReinstate }: PlayerCardProps) {
  const isBenched = !player.is_active
  const roleColor = getRoleColor(player.role)
  const xPTS =
    player.adjusted_score != null
      ? player.adjusted_score
      : player.rolling_avg != null
      ? player.rolling_avg * player.elo_multiplier
      : null

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16, scale: 0.97 }}
      animate={{ opacity: isBenched ? 0.45 : 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      whileHover={{ scale: 1.02, y: -2 }}
      transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
      className="relative group rounded-xl overflow-hidden border"
      style={{
        background: '#151b26',
        borderColor: 'rgba(255,255,255,0.07)',
        boxShadow: isBenched ? 'none' : '0 4px 20px rgba(0,200,150,0.06)',
      }}
    >
      {/* Top role-color accent bar */}
      <div
        className="h-[3px] w-full"
        style={{ background: `linear-gradient(90deg, ${roleColor}, ${roleColor}88)` }}
      />

      {/* Benched overlay */}
      {isBenched && (
        <div className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none" style={{ top: 3 }}>
          <span className="px-3 py-1 rounded-full text-[10px] font-black tracking-widest bg-black/60 text-slate-400 border border-white/10 uppercase">
            Benched
          </span>
        </div>
      )}

      {/* Bench / reinstate button — top right */}
      <div className="absolute top-2 right-2 z-20">
        {isBenched ? (
          <button
            onClick={onReinstate}
            className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30 transition-colors"
          >
            Reinstate
          </button>
        ) : (
          <button
            onClick={onBench}
            className="px-2 py-0.5 rounded text-[10px] font-semibold opacity-0 group-hover:opacity-100 transition-all duration-150"
            style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#64748b' }}
            onMouseEnter={e => {
              const btn = e.currentTarget
              btn.style.background = 'rgba(239,68,68,0.15)'
              btn.style.color = '#f87171'
              btn.style.borderColor = 'rgba(239,68,68,0.3)'
            }}
            onMouseLeave={e => {
              const btn = e.currentTarget
              btn.style.background = 'rgba(255,255,255,0.04)'
              btn.style.color = '#64748b'
              btn.style.borderColor = 'rgba(255,255,255,0.08)'
            }}
          >
            Bench
          </button>
        )}
      </div>

      <div className="px-3 pt-3 pb-3">
        {/* Top row: avatar + name + badges */}
        <div className="flex items-start gap-2.5">
          <Avatar photoUrl={player.photo_url} name={player.player_name} roleColor={roleColor} />

          <div className="flex-1 min-w-0 mt-0.5">
            <p className="text-sm font-bold text-white leading-tight truncate pr-14">
              {player.player_name}
            </p>
            <div className="flex items-center gap-1 mt-1 flex-wrap">
              <span
                className={cn('inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-black border')}
                style={{ background: roleColor + '18', borderColor: roleColor + '40', color: roleColor }}
              >
                {roleShort(player.role)}
              </span>
              <FormBadge form={player.form_state} />
            </div>
          </div>
        </div>

        {/* xPTS + Credits */}
        <div className="mt-3 flex items-end gap-3">
          <div className="flex-1">
            <p className="text-[10px] text-slate-500 mb-0.5">xPTS</p>
            <p className="text-2xl font-black leading-none" style={{ color: '#00c896' }}>
              {xPTS != null ? fmt(xPTS) : '—'}
            </p>
          </div>
          <div className="text-right">
            <p className="text-[10px] text-slate-500 mb-0.5">Credits</p>
            <p className="text-xl font-black text-white leading-none">
              {player.credits.toFixed(1)}
            </p>
          </div>
        </div>

        {/* Elo bar */}
        <EloBar multiplier={player.elo_multiplier} roleColor={roleColor} />
      </div>
    </motion.div>
  )
}
