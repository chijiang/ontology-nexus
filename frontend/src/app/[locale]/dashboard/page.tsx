// frontend/src/app/dashboard/page.tsx
'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { AppLayout } from '@/components/layout'
import { Chat } from '@/components/chat'
import { GraphPreview } from '@/components/graph-preview'
import { ConversationSidebar } from '@/components/conversation-sidebar'
import { useAuthStore } from '@/lib/auth'
import { conversationApi, Message } from '@/lib/api'
import { MessageSquare, Network, PanelLeftClose, PanelLeft } from 'lucide-react'

export default function DashboardPage() {
  const router = useRouter()
  const t = useTranslations()
  const token = useAuthStore((state) => state.token)
  const [graphData, setGraphData] = useState<any>(null)
  const [isHydrated, setIsHydrated] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null)
  const [initialMessages, setInitialMessages] = useState<Message[]>([])

  useEffect(() => {
    setIsHydrated(true)
  }, [])

  useEffect(() => {
    if (isHydrated && !token) {
      router.push('/')
    }
  }, [isHydrated, token, router])

  // Load conversation messages
  const loadConversation = useCallback(async (id: number | null) => {
    setActiveConversationId(id)
    setGraphData(null)

    if (id) {
      try {
        const res = await conversationApi.get(id)
        setInitialMessages(res.data.messages)

        // If there is graph_data, display the last one
        const lastWithGraph = [...res.data.messages]
          .reverse()
          .find(m => m.extra_metadata?.graph_data)
        if (lastWithGraph?.extra_metadata?.graph_data) {
          setGraphData(lastWithGraph.extra_metadata.graph_data)
        }
      } catch (err) {
        console.error('Failed to load conversation:', err)
        setInitialMessages([])
      }
    } else {
      setInitialMessages([])
    }
  }, [])

  const handleNewChat = () => {
    setActiveConversationId(null)
    setInitialMessages([])
    setGraphData(null)
  }

  const handleConversationCreated = (id: number) => {
    setActiveConversationId(id)
  }

  if (!isHydrated || !token) {
    return null
  }

  return (
    <AppLayout noPadding>
      <div className="flex flex-1 h-full overflow-hidden relative">
        {/* Toggle sidebar button (Floating when closed) */}
        {!sidebarOpen && (
          <button
            onClick={() => setSidebarOpen(true)}
            className="absolute left-4 top-4 z-20 p-2.5 bg-white border border-slate-200 rounded-lg shadow-md hover:bg-slate-50 transition-all text-slate-500 hover:text-indigo-600"
            title={t('layout.showSidebar')}
          >
            <PanelLeft className="h-4 w-4" />
          </button>
        )}

        {/* Sidebar */}
        <div className={`transition-all duration-300 ease-in-out ${sidebarOpen ? 'w-64' : 'w-0'} flex-shrink-0 overflow-hidden h-full`}>
          <ConversationSidebar
            activeId={activeConversationId}
            onSelect={loadConversation}
            onNewChat={handleNewChat}
            onToggle={() => setSidebarOpen(false)}
          />
        </div>

        {/* Main content */}
        <div className="flex-1 min-h-0 bg-slate-50 p-4 lg:p-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full overflow-hidden">
            {/* Q&A area */}
            <div className="flex flex-col bg-white rounded-2xl shadow-lg border border-slate-200 overflow-hidden h-full min-h-0">
              <div className="flex items-center gap-2 px-5 py-4 border-b border-slate-100 bg-slate-50 flex-shrink-0">
                <div className="p-2 rounded-lg bg-indigo-600">
                  <MessageSquare className="h-5 w-5 text-white" />
                </div>
                <h2 className="text-lg font-semibold text-slate-800">{t('dashboard.title')}</h2>
              </div>
              <div className="flex-1 min-h-0">
                <Chat
                  onGraphData={setGraphData}
                  conversationId={activeConversationId}
                  initialMessages={initialMessages}
                  onConversationCreated={handleConversationCreated}
                />
              </div>
            </div>

            {/* Graph area */}
            <div className="flex flex-col bg-slate-900 rounded-2xl shadow-lg overflow-hidden h-full min-h-0">
              <div className="flex items-center gap-2 px-5 py-4 border-b border-slate-700 flex-shrink-0">
                <div className="p-2 rounded-lg bg-emerald-600">
                  <Network className="h-5 w-5 text-white" />
                </div>
                <h2 className="text-lg font-semibold text-white">{t('dashboard.graphPreview')}</h2>
              </div>
              <div className="flex-1 min-h-0">
                <GraphPreview data={graphData} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
