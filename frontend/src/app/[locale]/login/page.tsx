'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations, useLocale } from 'next-intl'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { authApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { toast } from 'sonner'
import { Eye, EyeOff } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const locale = useLocale()
  const t = useTranslations()
  const { user, token, setAuth } = useAuthStore()
  const [isLogin, setIsLogin] = useState(true)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  useEffect(() => {
    if (token) {
      router.replace(`/${locale}/dashboard`)
    }
  }, [token, locale, router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      if (isLogin) {
        const res = await authApi.login(username, password)
        setAuth({ id: 0, username: username }, res.data.access_token)
        toast.success(t('auth.loginSuccess'))
        router.push(`/${locale}/dashboard`)
      } else {
        await authApi.register(username, password, email)
        toast.success(t('auth.registerSuccess'))
        setIsLogin(true)
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || t('common.error'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center bg-cover bg-center bg-no-repeat relative"
      style={{ backgroundImage: 'url("/backend-1.png")' }}
    >
      <Card className="w-full max-w-md relative z-10 bg-white/80 backdrop-blur-sm shadow-2xl border-white/20">
        <CardHeader>
          <CardTitle>{isLogin ? t('auth.login') : t('auth.register')}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              placeholder={t('auth.username')}
              name="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="off"
              required
            />
            {!isLogin && (
              <Input
                placeholder={t('auth.emailOptional')}
                type="email"
                name="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="off"
              />
            )}
            <div className="relative">
              <Input
                placeholder={t('auth.password')}
                type={showPassword ? "text" : "password"}
                name="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={isLogin ? "current-password" : "new-password"}
                className="pr-10"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            <Button type="submit" className="w-full bg-primary hover:opacity-90" disabled={loading}>
              {loading ? t('common.loading') : isLogin ? t('auth.login') : t('auth.register')}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm">
            {isLogin ? t('auth.noAccount') : t('auth.hasAccount')}{'  '}
            <button
              type="button"
              onClick={() => setIsLogin(!isLogin)}
              className="text-primary hover:underline"
            >
              {isLogin ? t('auth.register') : t('auth.login')}
            </button>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
