import { useMemo } from 'react'
import { motion } from 'framer-motion'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { Shield, Zap, Scale } from 'lucide-react'
import type { EvoPoint } from '@/types'
import { cn, fmt } from '@/lib/utils'

interface EvoProgress {
  safe: EvoPoint[]
  explosive: EvoPoint[]
  balanced: EvoPoint[]
}

interface EvolutionDashboardProps {
  progress: EvoProgress
  currentStrategy: string
  totalGenerations?: number
}

const STRATEGY_META = {
  safe: {
    label: 'Safe Team',
    icon: Shield,
    color: '#3b82f6',
    colorMuted: '#3b82f620',
    colorBorder: '#3b82f640',
    gradient: ['#1d4ed8', '#3b82f6'],
  },
  explosive: {
    label: 'Explosive Team',
    icon: Zap,
    color: '#f97316',
    colorMuted: '#f9731620',
    colorBorder: '#f9731640',
    gradient: ['#c2410c', '#f97316'],
  },
  balanced: {
    label: 'Balanced Team',
    icon: Scale,
    color: '#a855f7',
    colorMuted: '#a855f720',
    colorBorder: '#a855f740',
    gradient: ['#7e22ce', '#a855f7'],
  },
}

function getCurrentGeneration(progress: EvoProgress): number {
  const all = [
    ...progress.safe,
    ...progress.explosive,
    ...progress.balanced,
  ]
  if (all.length === 0) return 0
  return Math.max(...all.map(p => p.generation))
}

function getLatestFitness(points: EvoPoint[]): number | null {
  if (points.length === 0) return null
  return points[points.length - 1].fitness
}

interface ChartCardProps {
  strategyKey: 'safe' | 'explosive' | 'balanced'
  points: EvoPoint[]
  isActive: boolean
  totalGenerations: number
}

function ChartCard({ strategyKey, points, isActive, totalGenerations }: ChartCardProps) {
  const meta = STRATEGY_META[strategyKey]
  const Icon = meta.icon
  const latestFitness = getLatestFitness(points)
  const progress = points.length > 0 ? (points.length / totalGenerations) * 100 : 0

  const chartData = useMemo(() => {
    if (points.length === 0) {
      return [{ generation: 0, fitness: 0 }, { generation: totalGenerations, fitness: 0 }]
    }
    return points
  }, [points, totalGenerations])

  return (
    <motion.div
      layout
      className={cn(
        'relative rounded-2xl overflow-hidden flex flex-col',
        'border transition-all duration-500',
        isActive
          ? 'border-opacity-80 shadow-2xl'
          : 'border-white/[0.08]'
      )}
      style={
        isActive
          ? {
              borderColor: meta.color + '60',
              boxShadow: `0 0 40px ${meta.color}25, 0 0 80px ${meta.color}10, inset 0 0 40px ${meta.color}05`,
              background: `linear-gradient(135deg, ${meta.color}08 0%, rgba(255,255,255,0.03) 100%)`,
            }
          : {
              background: 'rgba(255,255,255,0.04)',
            }
      }
    >
      {/* Top glow bar when active */}
      {isActive && (
        <div
          className="absolute top-0 left-0 right-0 h-[2px]"
          style={{
            background: `linear-gradient(90deg, transparent, ${meta.color}, ${meta.color}, transparent)`,
            animation: 'pulse 2s ease-in-out infinite',
          }}
        />
      )}

      {/* Active indicator pulse */}
      {isActive && (
        <div className="absolute top-3 right-3 flex items-center gap-1.5">
          <span
            className="w-2 h-2 rounded-full animate-ping absolute"
            style={{ background: meta.color }}
          />
          <span
            className="w-2 h-2 rounded-full relative"
            style={{ background: meta.color }}
          />
        </div>
      )}

      <div className="p-4 flex-1 flex flex-col">
        {/* Header */}
        <div className="flex items-center gap-2 mb-4">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: meta.color + '20', border: `1px solid ${meta.color}30` }}
          >
            <Icon className="w-4 h-4" style={{ color: meta.color }} />
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-white/70">
              {meta.label}
            </p>
            <p className="text-xs text-slate-500">
              {points.length > 0 ? `${points.length} generations` : 'Waiting…'}
            </p>
          </div>
        </div>

        {/* Chart */}
        <div className="flex-1 min-h-[120px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 4, right: 4, left: -32, bottom: 0 }}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.04)"
                vertical={false}
              />
              <XAxis dataKey="generation" hide />
              <YAxis hide />
              <Tooltip
                contentStyle={{
                  background: '#0f0f17',
                  border: `1px solid ${meta.color}40`,
                  borderRadius: '8px',
                  fontSize: '11px',
                  color: '#fff',
                }}
                labelFormatter={(v) => `Gen ${v}`}
                formatter={(v: number) => [fmt(v, 2), 'Fitness']}
              />
              <Line
                type="monotone"
                dataKey="fitness"
                stroke={meta.color}
                strokeWidth={points.length > 0 ? 2 : 1}
                dot={false}
                activeDot={{ r: 4, fill: meta.color }}
                strokeDasharray={points.length === 0 ? '6 4' : undefined}
                strokeOpacity={points.length === 0 ? 0.3 : 1}
                isAnimationActive={true}
                animationDuration={300}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Fitness value */}
        <div className="mt-3 pt-3 border-t border-white/[0.06]">
          <div className="flex items-end justify-between">
            <div>
              <p className="text-xs text-slate-500 mb-0.5">Current Fitness</p>
              <p
                className="text-2xl font-black leading-none"
                style={{ color: latestFitness != null ? meta.color : '#475569' }}
              >
                {latestFitness != null ? fmt(latestFitness, 3) : '—'}
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-500 mb-0.5">Progress</p>
              <p className="text-sm font-bold text-white">{Math.round(progress)}%</p>
            </div>
          </div>
          {/* Mini progress bar */}
          <div className="mt-2 h-1 rounded-full bg-white/[0.06] overflow-hidden">
            <motion.div
              className="h-full rounded-full"
              style={{ background: `linear-gradient(90deg, ${meta.gradient[0]}, ${meta.gradient[1]})` }}
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
            />
          </div>
        </div>
      </div>
    </motion.div>
  )
}

export default function EvolutionDashboard({
  progress,
  currentStrategy,
  totalGenerations = 150,
}: EvolutionDashboardProps) {
  const currentGen = getCurrentGeneration(progress)
  const totalDone =
    progress.safe.length + progress.explosive.length + progress.balanced.length
  const overallProgress = (totalDone / (totalGenerations * 3)) * 100

  const activeStrategyMeta = STRATEGY_META[currentStrategy as keyof typeof STRATEGY_META]
  const ActiveIcon = activeStrategyMeta?.icon ?? Zap

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-start pt-8 pb-12 px-4 sm:px-6 relative overflow-hidden"
      style={{ background: '#0a0a0f' }}
    >
      {/* Ambient glow */}
      <div
        className="pointer-events-none fixed inset-0"
        style={{
          background:
            'radial-gradient(ellipse 70% 50% at 50% 10%, rgba(99,102,241,0.07) 0%, transparent 60%)',
        }}
      />

      {/* Floating particles */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        {[...Array(12)].map((_, i) => (
          <div
            key={i}
            className="absolute rounded-full"
            style={{
              width: `${2 + (i % 3)}px`,
              height: `${2 + (i % 3)}px`,
              left: `${8 + i * 7.5}%`,
              top: `${15 + (i % 5) * 15}%`,
              background:
                i % 3 === 0
                  ? '#3b82f640'
                  : i % 3 === 1
                  ? '#f9731640'
                  : '#a855f740',
              animation: `float-particle ${3 + (i % 4)}s ease-in-out ${i * 0.4}s infinite alternate`,
            }}
          />
        ))}
      </div>

      <div className="relative z-10 w-full max-w-5xl flex flex-col gap-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <p className="text-xs font-bold tracking-[0.3em] uppercase text-slate-500 mb-3">
            Genetic Algorithm · Running
          </p>
          <div className="flex items-center justify-center gap-3">
            <motion.div
              key={currentGen}
              initial={{ scale: 1.3, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.3 }}
              className="text-5xl sm:text-6xl font-black text-white tabular-nums"
            >
              {String(currentGen).padStart(3, '0')}
            </motion.div>
            <div className="text-left">
              <p className="text-slate-500 text-sm font-semibold leading-tight">GENERATION</p>
              <p className="text-slate-600 text-xs">/ {totalGenerations}</p>
            </div>
          </div>
        </motion.div>

        {/* Current strategy indicator */}
        <motion.div
          key={currentStrategy}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.35 }}
          className="flex items-center justify-center"
        >
          <div
            className="inline-flex items-center gap-3 px-6 py-3 rounded-2xl border"
            style={{
              background: activeStrategyMeta
                ? activeStrategyMeta.color + '12'
                : 'rgba(255,255,255,0.04)',
              borderColor: activeStrategyMeta
                ? activeStrategyMeta.color + '40'
                : 'rgba(255,255,255,0.08)',
              boxShadow: activeStrategyMeta
                ? `0 0 24px ${activeStrategyMeta.color}20`
                : 'none',
            }}
          >
            <div
              className="w-8 h-8 rounded-xl flex items-center justify-center"
              style={{
                background: activeStrategyMeta
                  ? activeStrategyMeta.color + '25'
                  : 'rgba(255,255,255,0.06)',
              }}
            >
              <ActiveIcon
                className="w-4 h-4"
                style={{ color: activeStrategyMeta?.color ?? '#6366f1' }}
              />
            </div>
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold">
                Optimizing
              </p>
              <p
                className="text-sm font-bold"
                style={{ color: activeStrategyMeta?.color ?? '#fff' }}
              >
                {activeStrategyMeta?.label ?? 'Team'}
              </p>
            </div>
            <div className="flex gap-1 ml-2">
              <span
                className="w-1.5 h-1.5 rounded-full animate-bounce"
                style={{
                  background: activeStrategyMeta?.color ?? '#6366f1',
                  animationDelay: '0ms',
                }}
              />
              <span
                className="w-1.5 h-1.5 rounded-full animate-bounce"
                style={{
                  background: activeStrategyMeta?.color ?? '#6366f1',
                  animationDelay: '150ms',
                }}
              />
              <span
                className="w-1.5 h-1.5 rounded-full animate-bounce"
                style={{
                  background: activeStrategyMeta?.color ?? '#6366f1',
                  animationDelay: '300ms',
                }}
              />
            </div>
          </div>
        </motion.div>

        {/* Three chart cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {(['safe', 'explosive', 'balanced'] as const).map((key, i) => (
            <motion.div
              key={key}
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
            >
              <ChartCard
                strategyKey={key}
                points={progress[key]}
                isActive={currentStrategy === key}
                totalGenerations={totalGenerations}
              />
            </motion.div>
          ))}
        </div>

        {/* Overall progress bar */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-5"
        >
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Overall Progress
            </p>
            <p className="text-sm font-black text-white">
              {Math.round(overallProgress)}%
            </p>
          </div>
          <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden flex">
            {/* Safe segment */}
            <motion.div
              className="h-full"
              style={{ background: 'linear-gradient(90deg, #1d4ed8, #3b82f6)' }}
              initial={{ width: 0 }}
              animate={{
                width: `${(progress.safe.length / (totalGenerations * 3)) * 100}%`,
              }}
              transition={{ duration: 0.4 }}
            />
            {/* Explosive segment */}
            <motion.div
              className="h-full"
              style={{ background: 'linear-gradient(90deg, #c2410c, #f97316)' }}
              initial={{ width: 0 }}
              animate={{
                width: `${(progress.explosive.length / (totalGenerations * 3)) * 100}%`,
              }}
              transition={{ duration: 0.4 }}
            />
            {/* Balanced segment */}
            <motion.div
              className="h-full"
              style={{ background: 'linear-gradient(90deg, #7e22ce, #a855f7)' }}
              initial={{ width: 0 }}
              animate={{
                width: `${(progress.balanced.length / (totalGenerations * 3)) * 100}%`,
              }}
              transition={{ duration: 0.4 }}
            />
          </div>
          {/* Legend */}
          <div className="flex items-center gap-4 mt-3">
            {(['safe', 'explosive', 'balanced'] as const).map(key => {
              const meta = STRATEGY_META[key]
              const pts = progress[key].length
              return (
                <div key={key} className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full" style={{ background: meta.color }} />
                  <span className="text-xs text-slate-500 font-medium capitalize">{key}</span>
                  <span className="text-xs font-bold" style={{ color: meta.color }}>
                    {pts}/{totalGenerations}
                  </span>
                </div>
              )
            })}
          </div>
        </motion.div>
      </div>

      <style>{`
        @keyframes float-particle {
          0% { transform: translateY(0px) scale(1); opacity: 0.4; }
          100% { transform: translateY(-20px) scale(1.3); opacity: 0.8; }
        }
      `}</style>
    </div>
  )
}
