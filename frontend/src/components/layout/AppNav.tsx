import { Link, useLocation } from 'react-router-dom'

interface AppNavProps {
  teamA?: string
  teamB?: string
}

export default function AppNav({ teamA, teamB }: AppNavProps) {
  const location = useLocation()
  const hasMatch = teamA && teamB

  return (
    <nav
      className="sticky top-0 z-50 flex items-center px-4 sm:px-6 border-b backdrop-blur-xl"
      style={{ height: 52, background: '#10151e', borderColor: 'rgba(255,255,255,0.06)' }}
    >
      {/* Left: wordmark */}
      <Link to="/" className="flex items-center gap-2 flex-shrink-0 no-underline">
        <span
          className="w-2 h-2 rounded-full"
          style={{ background: '#00c896', boxShadow: '0 0 6px #00c896' }}
        />
        <span className="text-white font-black text-sm tracking-tight">
          Draft<span style={{ color: '#00c896' }}>Genius</span>
        </span>
      </Link>

      {/* Center: breadcrumb */}
      <div className="flex-1 flex items-center justify-center gap-1.5 text-xs text-slate-500">
        <Link to="/" className="hover:text-slate-300 transition-colors">
          Home
        </Link>
        {hasMatch && (
          <>
            <span>›</span>
            <span className="text-slate-400 hidden sm:inline">
              {teamA} vs {teamB}
            </span>
            <span className="text-slate-400 sm:hidden">
              Match
            </span>
            {location.pathname === '/results' && (
              <>
                <span>›</span>
                <span className="text-slate-300">Results</span>
              </>
            )}
          </>
        )}
      </div>

      {/* Right: spacer to balance wordmark */}
      <div className="flex-shrink-0" style={{ width: 104 }} />
    </nav>
  )
}
