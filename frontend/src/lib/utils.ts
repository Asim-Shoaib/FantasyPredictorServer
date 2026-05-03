import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function fmt(n: number | null | undefined, decimals = 1): string {
  if (n == null) return '—'
  return n.toFixed(decimals)
}

export function roleBadgeColor(role: string): string {
  const r = role.toLowerCase()
  if (r.includes('wicket') || r === 'wk' || r === 'wk-batter') return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30'
  if (r.includes('bowler') || r.includes('bowl')) return 'bg-red-500/20 text-red-300 border-red-500/30'
  if (r.includes('all')) return 'bg-purple-500/20 text-purple-300 border-purple-500/30'
  return 'bg-blue-500/20 text-blue-300 border-blue-500/30'
}

export function roleShort(role: string): string {
  const r = role.toLowerCase()
  if (r.includes('wicket') || r === 'wk' || r === 'wk-batter') return 'WK'
  if (r.includes('all')) return 'AR'
  if (r.includes('bowl')) return 'BWL'
  return 'BAT'
}
