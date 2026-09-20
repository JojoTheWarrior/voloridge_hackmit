import { Menu } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, Outlet } from 'react-router-dom'
import { CastleLogo } from './CastleLogo'
import { Sidebar } from './Sidebar'
import { ThemeToggle } from './ThemeToggle'

export function AppShell() {
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    if (!menuOpen) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMenuOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [menuOpen])

  return (
    <div className="flex h-dvh print:block print:h-auto">
      <aside className="hidden md:block print:hidden">
        <Sidebar />
      </aside>

      {menuOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <button
            type="button"
            aria-label="Close menu"
            onClick={() => setMenuOpen(false)}
            className="fade-in absolute inset-0 bg-scrim"
          />
          <div className="slide-in relative h-full w-60">
            <Sidebar onNavigate={() => setMenuOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 shrink-0 items-center gap-3 border-b border-line-soft px-4 md:px-6 print:hidden">
          <button type="button" aria-label="Open menu" aria-expanded={menuOpen} onClick={() => setMenuOpen(true)} className="-ml-1 p-1 md:hidden">
            <Menu size={18} strokeWidth={1.75} aria-hidden="true" />
          </button>
          <Link to="/" aria-label="kingdom" className="flex items-center gap-2 text-[15px] font-medium tracking-tight md:hidden">
            <CastleLogo />
            <span aria-hidden="true">kingdom</span>
          </Link>
          <div className="ml-auto"><ThemeToggle /></div>
        </header>
        <main className="min-h-0 flex-1 overflow-y-auto print:overflow-visible">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
