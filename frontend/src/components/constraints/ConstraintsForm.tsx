import { useState } from 'react'
import { motion } from 'framer-motion'
import { ArrowRight, Zap } from 'lucide-react'
import { getFranchise } from '@/constants/franchises'
import { cn } from '@/lib/utils'

export interface Constraints {
  budget: number
  batter_min: number
  batter_max: number
  allrounder_min: number
  allrounder_max: number
  wicketkeeper_min: number
  wicketkeeper_max: number
  bowler_min: number
  bowler_max: number
  per_team_min: number
  per_team_max: number
}

interface ConstraintsFormProps {
  teamA: string
  teamB: string
  onSubmit: (constraints: Constraints) => void
  isLoading?: boolean
}

const DEFAULT_CONSTRAINTS: Constraints = {
  budget: 100,
  batter_min: 2,
  batter_max: 5,
  allrounder_min: 1,
  allrounder_max: 3,
  wicketkeeper_min: 1,
  wicketkeeper_max: 1,
  bowler_min: 2,
  bowler_max: 4,
  per_team_min: 4,
  per_team_max: 7,
}

export function ConstraintsForm({ teamA, teamB, onSubmit, isLoading }: ConstraintsFormProps) {
  const [constraints, setConstraints] = useState<Constraints>(DEFAULT_CONSTRAINTS)

  const franchiseA = getFranchise(teamA)
  const franchiseB = getFranchise(teamB)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(constraints)
  }

  const handleConstraintChange = (key: keyof Constraints, value: number) => {
    setConstraints(prev => ({
      ...prev,
      [key]: Math.max(0, value),
    }))
  }

  const totalMin = constraints.batter_min + constraints.allrounder_min + constraints.wicketkeeper_min + constraints.bowler_min
  const totalMax = constraints.batter_max + constraints.allrounder_max + constraints.wicketkeeper_max + constraints.bowler_max
  const isValid = totalMin <= 11 && totalMax >= 11 && constraints.budget > 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen flex items-center justify-center px-4 py-8"
      style={{ background: '#0a0a0f' }}
    >
      <div className="w-full max-w-2xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="text-center mb-8"
        >
          <h1 className="text-3xl sm:text-4xl font-black text-white mb-2">
            Set Your Constraints
          </h1>
          <p className="text-slate-400 text-sm">
            Define your squad composition rules and budget limits
          </p>

          {/* Team badges */}
          <div className="flex items-center justify-center gap-3 mt-6">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
              style={{ background: franchiseA.primary + '15', border: `1px solid ${franchiseA.primary}40` }}>
              <span className="text-lg">{franchiseA.emoji}</span>
              <span className="text-sm font-bold text-white">{teamA}</span>
            </div>
            <span className="text-slate-500 text-xs">vs</span>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
              style={{ background: franchiseB.primary + '15', border: `1px solid ${franchiseB.primary}40` }}>
              <span className="text-lg">{franchiseB.emoji}</span>
              <span className="text-sm font-bold text-white">{teamB}</span>
            </div>
          </div>
        </motion.div>

        {/* Form card */}
        <motion.form
          onSubmit={handleSubmit}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="p-6 sm:p-8 rounded-2xl border border-white/[0.1] backdrop-blur-xl"
          style={{
            background: 'radial-gradient(ellipse at top right, rgba(99,102,241,0.05), transparent 50%), rgba(255,255,255,0.02)',
          }}
        >
          {/* Budget Section */}
          <div className="mb-8">
            <label className="block text-white font-bold text-sm mb-3">
              Total Budget
            </label>
            <div className="relative">
              <input
                type="number"
                value={constraints.budget}
                onChange={(e) => handleConstraintChange('budget', parseInt(e.target.value) || 0)}
                className="w-full px-4 py-3 rounded-lg bg-white/[0.05] border border-white/[0.1] text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/30 transition-all"
              />
              <span className="absolute right-4 top-3 text-slate-500 text-sm">Credits</span>
            </div>
            <p className="text-xs text-slate-500 mt-2">Available budget for your squad</p>
          </div>

          {/* Role Constraints Grid */}
          <div className="mb-8">
            <h3 className="text-white font-bold text-sm mb-4">Player Role Distribution</h3>
            <div className="grid grid-cols-2 gap-4">
              {[
                { label: 'Batters', minKey: 'batter_min', maxKey: 'batter_max', color: '#3b82f6' },
                { label: 'All-Rounders', minKey: 'allrounder_min', maxKey: 'allrounder_max', color: '#8b5cf6' },
                { label: 'Wicket-Keepers', minKey: 'wicketkeeper_min', maxKey: 'wicketkeeper_max', color: '#ec4899' },
                { label: 'Bowlers', minKey: 'bowler_min', maxKey: 'bowler_max', color: '#f59e0b' },
              ].map(({ label, minKey, maxKey, color }) => (
                <div key={label} className="p-4 rounded-lg bg-white/[0.03] border border-white/[0.08]">
                  <label className="text-xs font-bold text-white mb-3 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full" style={{ background: color }} />
                    {label}
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min="0"
                      max="11"
                      value={constraints[minKey as keyof typeof constraints]}
                      onChange={(e) => handleConstraintChange(minKey as keyof Constraints, parseInt(e.target.value) || 0)}
                      className="w-12 px-2 py-1.5 rounded bg-white/[0.05] border border-white/[0.1] text-white text-xs text-center focus:outline-none focus:border-indigo-500/50"
                    />
                    <span className="text-slate-500 text-xs">-</span>
                    <input
                      type="number"
                      min="0"
                      max="11"
                      value={constraints[maxKey as keyof typeof constraints]}
                      onChange={(e) => handleConstraintChange(maxKey as keyof Constraints, parseInt(e.target.value) || 0)}
                      className="w-12 px-2 py-1.5 rounded bg-white/[0.05] border border-white/[0.1] text-white text-xs text-center focus:outline-none focus:border-indigo-500/50"
                    />
                  </div>
                </div>
              ))}
            </div>
            <p className="text-xs text-slate-500 mt-3">Define min-max for each player role</p>
          </div>

          {/* Per-Team Distribution */}
          <div className="mb-8">
            <h3 className="text-white font-bold text-sm mb-4">Per-Team Player Limit</h3>
            <div className="p-4 rounded-lg bg-white/[0.03] border border-white/[0.08]">
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min="0"
                  max="11"
                  value={constraints.per_team_min}
                  onChange={(e) => handleConstraintChange('per_team_min', parseInt(e.target.value) || 0)}
                  className="flex-1 px-3 py-2 rounded bg-white/[0.05] border border-white/[0.1] text-white text-sm focus:outline-none focus:border-indigo-500/50"
                />
                <span className="text-slate-500 text-sm">-</span>
                <input
                  type="number"
                  min="0"
                  max="11"
                  value={constraints.per_team_max}
                  onChange={(e) => handleConstraintChange('per_team_max', parseInt(e.target.value) || 0)}
                  className="flex-1 px-3 py-2 rounded bg-white/[0.05] border border-white/[0.1] text-white text-sm focus:outline-none focus:border-indigo-500/50"
                />
                <span className="text-slate-500 text-sm">players/team</span>
              </div>
            </div>
            <p className="text-xs text-slate-500 mt-2">Minimum and maximum players per team in the XI</p>
          </div>

          {/* Validation info */}
          <div className={cn(
            'mb-6 p-4 rounded-lg border text-sm transition-all',
            isValid
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
          )}>
            <div className="font-semibold mb-1">
              Squad Range: {totalMin} - {totalMax} players
            </div>
            {!isValid && (
              <p className="text-xs opacity-75">
                Must be able to select exactly 11 players (min={totalMin}, max={totalMax})
              </p>
            )}
          </div>

          {/* Submit button */}
          <motion.button
            type="submit"
            disabled={!isValid || isLoading}
            whileHover={isValid ? { scale: 1.02 } : {}}
            whileTap={isValid ? { scale: 0.98 } : {}}
            className="w-full py-4 rounded-lg font-bold text-white flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            style={
              isValid
                ? {
                    background: `linear-gradient(135deg, ${franchiseA.primary}, ${franchiseB.primary})`,
                    boxShadow: `0 0 20px ${franchiseA.primary}40`,
                  }
                : {
                    background: 'rgba(255,255,255,0.05)',
                    boxShadow: 'none',
                  }
            }
          >
            <Zap className="w-4 h-4" />
            {isLoading ? 'Generating...' : 'Generate Fantasy XI'}
            {!isLoading && <ArrowRight className="w-4 h-4" />}
          </motion.button>
        </motion.form>
      </div>
    </motion.div>
  )
}
