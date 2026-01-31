// frontend/src/components/layout.tsx
'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/lib/auth'

export function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout } = useAuthStore()

  const handleLogout = () => {
    logout()
    router.push('/')
  }

  const navItems = [
    { href: '/dashboard', label: '问答' },
    { href: '/config', label: '配置' },
    { href: '/graph/import', label: '导入图谱' },
    { href: '/graph/visualize', label: '图谱可视化' },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold">知识图谱问答</h1>
          <nav className="flex items-center gap-4">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`text-sm ${
                  pathname === item.href ? 'font-bold text-blue-600' : 'text-gray-600'
                }`}
              >
                {item.label}
              </Link>
            ))}
            {user && (
              <>
                <span className="text-sm text-gray-600">欢迎, {user.username}</span>
                <Button variant="ghost" size="sm" onClick={handleLogout}>
                  登出
                </Button>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="container mx-auto px-4 py-8">{children}</main>
    </div>
  )
}
