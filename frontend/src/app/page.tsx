// frontend/src/app/page.tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { authApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { toast } from 'sonner'

export default function LoginPage() {
  const router = useRouter()
  const setAuth = useAuthStore((state) => state.setAuth)
  const [isLogin, setIsLogin] = useState(true)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      if (isLogin) {
        const res = await authApi.login(username, password)
        setAuth({ id: 0, username: username }, res.data.access_token)
        toast.success('登录成功')
        router.push('/dashboard')
      } else {
        await authApi.register(username, password, email)
        toast.success('注册成功，请登录')
        setIsLogin(true)
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '操作失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>{isLogin ? '登录' : '注册'}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              placeholder="用户名"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
            {!isLogin && (
              <Input
                placeholder="邮箱（可选）"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            )}
            <Input
              placeholder="密码"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? '处理中...' : isLogin ? '登录' : '注册'}
            </Button>
          </form>
          <p className="text-sm text-center mt-4">
            {isLogin ? '还没有账号？' : '已有账号？'}
            <button
              type="button"
              onClick={() => setIsLogin(!isLogin)}
              className="text-blue-600 hover:underline"
            >
              {isLogin ? '注册' : '登录'}
            </button>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
