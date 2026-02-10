// frontend/src/components/layout.tsx
'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useTranslations, useLocale } from 'next-intl'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/lib/auth'
import { LanguageSwitcher } from '@/components/language-switcher'
import { useMemo } from 'react'

export function AppLayout({ children, noPadding = false }: { children: React.ReactNode, noPadding?: boolean }) {
  const pathname = usePathname()
  const router = useRouter()
  const locale = useLocale()
  const { user, logout } = useAuthStore()
  const t = useTranslations()

  const handleLogout = () => {
    logout()
    router.push(`/${locale}`)
  }

  const navItems = useMemo(() => [
    { href: `/${locale}/dashboard`, label: t('nav.qa') },
    { href: `/${locale}/graph/import`, label: t('nav.importGraph') },
    { href: `/${locale}/graph/ontology`, label: t('nav.ontology') },
    { href: `/${locale}/graph/binding`, label: t('nav.binding') },
    { href: `/${locale}/graph/instances`, label: t('nav.instances') },
    { href: `/${locale}/data-products`, label: t('nav.dataProducts') },
    { href: `/${locale}/rules`, label: t('nav.rules') },
    { href: `/${locale}/config`, label: t('nav.config') },
  ], [locale, t])

  return (
    <div className={`flex flex-col bg-gray-50 ${noPadding ? 'h-screen overflow-hidden' : 'min-h-screen'}`}>
      <header className="bg-white border-b flex-shrink-0 sticky top-0 z-50">
        <div className="w-full px-6 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold text-primary">{t('layout.title')}</h1>
          <nav className="flex items-center gap-6">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`text-sm transition-colors ${pathname === item.href ? 'font-bold text-primary' : 'text-slate-600 hover:text-primary/70'
                  }`}
              >
                {item.label}
              </Link>
            ))}
            <LanguageSwitcher />
            {user && (
              <div className="flex items-center gap-4 pl-4 border-l border-gray-200">
                <span className="text-sm text-gray-600">{t('layout.welcomeUser', { username: user.username })}</span>
                <Button variant="ghost" size="sm" onClick={handleLogout} className="text-gray-500 hover:text-red-500">
                  {t('auth.logout')}
                </Button>
              </div>
            )}
          </nav>
        </div>
      </header>
      <main className={`flex-1 flex flex-col ${noPadding ? 'min-h-0 overflow-hidden' : 'container mx-auto px-4 py-8'}`}>{children}</main>
    </div>
  )
}
