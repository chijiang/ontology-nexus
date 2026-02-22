'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import { useMemo, useState, useEffect } from 'react'
import { useAuthStore } from '@/lib/auth'
import { usePermissions } from '@/hooks/usePermissions'
import { LanguageSwitcher } from '@/components/language-switcher'
import {
  Database,
  Network,
  CircleDot,
  Package,
  Scale,
  Settings,
  ChevronLeft,
  ChevronRight,
  Menu,
  Sparkles,
  LogOut,
  Search,
  Users,
  Shield
} from 'lucide-react'

export function AppLayout({ children, noPadding = false }: { children: React.ReactNode, noPadding?: boolean }) {
  const { permissions, loading: loadingPermissions, hasPageAccess } = usePermissions() // Ensure permissions are loaded globally
  const pathname = usePathname()
  const router = useRouter()
  const locale = useLocale()
  const { user, logout } = useAuthStore()
  const t = useTranslations()
  const [isNavExpanded, setIsNavExpanded] = useState(true)

  // Persist sidebar state
  useEffect(() => {
    const saved = localStorage.getItem('nav-sidebar-expanded')
    if (saved !== null) {
      setIsNavExpanded(saved === 'true')
    }
  }, [])

  const toggleNav = () => {
    const newState = !isNavExpanded
    setIsNavExpanded(newState)
    localStorage.setItem('nav-sidebar-expanded', String(newState))
  }

  const handleLogout = () => {
    logout()
    router.push(`/${locale}`)
  }
  // ... (existing code)

  const navItems = useMemo(() => {
    const items = [
      { id: 'chat', href: `/${locale}/dashboard`, label: t('nav.qa'), icon: Sparkles },
      { id: 'ontology', href: `/${locale}/graph/management`, label: t('nav.ontology'), icon: Network },
      { id: 'instances', href: `/${locale}/graph/instances`, label: t('nav.instances'), icon: CircleDot },
      { id: 'data-products', href: `/${locale}/data-products`, label: t('nav.dataProducts'), icon: Package },
      { id: 'rules', href: `/${locale}/rules`, label: t('nav.rules'), icon: Scale },
      { id: 'import', href: `/${locale}/graph/import`, label: t('nav.importGraph'), icon: Database },
      { id: 'config', href: `/${locale}/config`, label: t('nav.config'), icon: Settings },
    ]

    // Filter items based on permissions
    const filteredItems = items.filter(item => hasPageAccess(item.id))

    // Only show admin links to admin users or those with admin page permission
    if (user?.is_admin || permissions?.is_admin || hasPageAccess('admin')) {
      filteredItems.push(
        { id: 'admin_users', href: `/${locale}/admin/users`, label: t('nav.users'), icon: Users },
        { id: 'admin_roles', href: `/${locale}/admin/roles`, label: t('nav.roles'), icon: Shield }
      )
    }

    return filteredItems
  }, [locale, t, user, permissions, hasPageAccess])

  return (
    <div className="flex h-screen bg-slate-50/50 overflow-hidden">
      {/* Sidebar Navigation */}
      <aside
        className={`bg-white border-r border-slate-200/60 flex flex-col transition-all duration-300 ease-in-out z-50 ${isNavExpanded ? 'w-64' : 'w-16'
          }`}
      >
        {/* Sidebar Header: Logo */}
        <div className="h-14 flex items-center px-4 border-b border-slate-100/50 flex-shrink-0">
          <Link href={`/${locale}/dashboard`} className={`flex items-center gap-3 transition-all ${isNavExpanded ? '' : 'mx-auto'}`}>
            <div className="w-8 h-8 flex-shrink-0 bg-primary rounded-lg flex items-center justify-center text-white text-[10px] font-bold shadow-sm shadow-primary/20 transition-transform hover:scale-105">
              EP
            </div>
          </Link>
        </div>

        {/* Unified Toggle Button Area */}
        <div className="h-10 flex items-center px-4 border-b border-slate-50/50 flex-shrink-0">
          <button
            onClick={toggleNav}
            className={`flex items-center gap-2 p-1.5 text-slate-400 hover:text-primary hover:bg-primary/5 rounded-lg transition-all w-full ${isNavExpanded ? 'justify-between' : 'justify-center'}`}
            title={isNavExpanded ? t('layout.hideSidebar') : t('layout.showSidebar')}
          >
            {isNavExpanded && <span className="text-[10px] font-bold uppercase tracking-widest ml-1">{t('common.menu') || 'Menu'}</span>}
            {isNavExpanded ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>
        </div>

        {/* Sidebar Links */}
        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto scrollbar-hide">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname?.startsWith(item.href + '/')
            const Icon = item.icon
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group relative ${isActive
                  ? 'bg-primary/5 text-primary shadow-sm shadow-primary/5'
                  : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                title={!isNavExpanded ? item.label : undefined}
              >
                <Icon className={`w-5 h-5 flex-shrink-0 ${isActive ? 'text-primary' : 'text-slate-400 group-hover:text-slate-600'}`} />
                {isNavExpanded && (
                  <span className="whitespace-nowrap transition-opacity duration-200">
                    {item.label}
                  </span>
                )}
                {!isNavExpanded && isActive && (
                  <div className="absolute left-0 w-1 h-6 bg-primary rounded-r-full" />
                )}
              </Link>
            )
          })}
        </nav>

        {/* Sidebar Footer: User (Optional small view) */}
        <div className="p-3 border-t border-slate-100/50">
          {/* Support or other footer links could go here */}
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-full relative overflow-hidden">
        {/* Top Header */}
        <header className="h-14 bg-white/80 backdrop-blur-md border-b border-slate-200/60 flex items-center justify-between px-6 flex-shrink-0 z-40">
          <div className="flex items-center">
            <h1 className="text-lg font-extrabold tracking-tight text-slate-900">
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary/70">
                {t('layout.title')}
              </span>
            </h1>
          </div>

          <div className="flex items-center gap-4">
            <LanguageSwitcher />

            {user && (
              <div className="flex items-center gap-3 pl-4 border-l border-slate-200">
                <div className="flex flex-col items-end">
                  <span className="text-[11px] font-semibold text-slate-900">{user.username}</span>
                  <button
                    onClick={handleLogout}
                    className="text-[9px] uppercase tracking-wider font-bold text-slate-400 hover:text-red-500 transition-colors"
                  >
                    {t('auth.logout')}
                  </button>
                </div>
                <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-slate-500 text-[10px] font-bold border-2 border-white shadow-sm ring-1 ring-slate-100">
                  {user.username.charAt(0).toUpperCase()}
                </div>
              </div>
            )}
          </div>
        </header>

        {/* Main Content */}
        <main
          className={`flex-1 overflow-hidden flex flex-col ${noPadding ? '' : 'p-6 lg:p-8 overflow-y-auto'
            }`}
        >
          <div className={noPadding ? 'flex-1 flex flex-col min-h-0' : 'max-w-[1600px] mx-auto w-full'}>
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
