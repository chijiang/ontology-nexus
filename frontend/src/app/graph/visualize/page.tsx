// frontend/src/app/graph/visualize/page.tsx
'use client'

import { useRouter } from 'next/navigation'
import { AppLayout } from '@/components/layout'
import { GraphViewer } from '@/components/graph-viewer'
import { useAuthStore } from '@/lib/auth'

export default function VisualizePage() {
  const router = useRouter()
  const token = useAuthStore((state) => state.token)

  if (!token) {
    router.push('/')
    return null
  }

  return (
    <AppLayout>
      <div className="h-[calc(100vh-200px)]">
        <GraphViewer />
      </div>
    </AppLayout>
  )
}
