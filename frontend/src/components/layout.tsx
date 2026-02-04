// frontend/src/components/layout.tsx
'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/lib/auth'

export function AppLayout({ children, noPadding = false }: { children: React.ReactNode, noPadding?: boolean }) {
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout } = useAuthStore()

  const handleLogout = () => {
    logout()
    router.push('/')
  }

  const navItems = [
    { href: '/dashboard', label: '问答' },
    { href: '/graph/import', label: '导入图谱' },
    { href: '/graph/ontology', label: '本体查看' },
    { href: '/graph/instances', label: '实例图谱' },
    { href: '/rules', label: '业务逻辑管理器' },
    { href: '/config', label: '系统配置' },
  ]

  return (
    <div className={`flex flex-col bg-gray-50 ${noPadding ? 'h-screen overflow-hidden' : 'min-h-screen'}`}>
      <header className="bg-white border-b flex-shrink-0 sticky top-0 z-50">
        <div className="w-full px-6 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold bg-indigo-600 bg-clip-text text-transparent">知识图谱问答</h1>
          <nav className="flex items-center gap-6">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`text-sm transition-colors ${pathname === item.href ? 'font-bold text-indigo-600' : 'text-gray-600 hover:text-indigo-400'
                  }`}
              >
                {item.label}
              </Link>
            ))}
            {user && (
              <div className="flex items-center gap-4 pl-4 border-l border-gray-200">
                <span className="text-sm text-gray-600">欢迎, {user.username}</span>
                <Button variant="ghost" size="sm" onClick={handleLogout} className="text-gray-500 hover:text-red-500">
                  登出
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
