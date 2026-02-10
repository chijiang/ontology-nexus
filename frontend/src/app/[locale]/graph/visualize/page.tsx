// frontend/src/app/graph/visualize/page.tsx
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { AppLayout } from '@/components/layout'
import { GraphViewer } from '@/components/graph-viewer'
import { SchemaViewer } from '@/components/schema-viewer'
import { useAuthStore } from '@/lib/auth'

export default function VisualizePage() {
  const router = useRouter()
  const t = useTranslations()
  const token = useAuthStore((state) => state.token)
  const [isHydrated, setIsHydrated] = useState(false)

  useEffect(() => {
    setIsHydrated(true)
  }, [])

  useEffect(() => {
    if (isHydrated && !token) {
      router.push('/')
    }
  }, [isHydrated, token, router])

  if (!isHydrated || !token) {
    return null
  }

  return (
    <AppLayout>
      <div className="h-[calc(100vh-160px)]">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-full">
          {/* Left: Schema View */}
          <div className="bg-white rounded-lg border overflow-hidden">
            <SchemaViewer />
          </div>

          {/* Right: Instance View */}
          <div className="bg-white rounded-lg border overflow-hidden">
            <GraphViewer />
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
