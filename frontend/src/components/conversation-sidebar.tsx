// frontend/src/components/conversation-sidebar.tsx
'use client'

import { useState, useEffect } from 'react'
import { conversationApi, Conversation } from '@/lib/api'
import { Plus, MessageSquare, Trash2, PanelLeftClose } from 'lucide-react'
import { useTranslations, useLocale } from 'next-intl'

interface ConversationSidebarProps {
    activeId: number | null
    onSelect: (id: number | null) => void
    onNewChat: () => void
    onToggle: () => void
}

export function ConversationSidebar({ activeId, onSelect, onNewChat, onToggle }: ConversationSidebarProps) {
    const t = useTranslations('components.conversation')
    const locale = useLocale()
    const [conversations, setConversations] = useState<Conversation[]>([])
    const [loading, setLoading] = useState(true)
    const [deletingId, setDeletingId] = useState<number | null>(null)

    const loadConversations = async () => {
        try {
            const res = await conversationApi.list()
            setConversations(res.data)
        } catch (err) {
            console.error('Failed to load conversations:', err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadConversations()
    }, [])

    // 重新加载对话列表
    useEffect(() => {
        const interval = setInterval(loadConversations, 5000)
        return () => clearInterval(interval)
    }, [])

    const handleDelete = async (id: number, e: React.MouseEvent) => {
        e.stopPropagation()
        if (deletingId) return // 防抖：正在删除中不再触发

        if (!confirm(t('deleteConfirm'))) return

        setDeletingId(id)
        try {
            await conversationApi.delete(id)
            setConversations(prev => prev.filter(c => c.id !== id))
            if (activeId === id) {
                onSelect(null)
            }
        } catch (err) {
            console.error('Failed to delete conversation:', err)
        } finally {
            setDeletingId(null)
        }
    }

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr)
        const now = new Date()
        const diff = now.getTime() - date.getTime()
        const days = Math.floor(diff / (1000 * 60 * 60 * 24))

        if (days === 0) return t('today')
        if (days === 1) return t('yesterday')
        if (days < 7) return t('daysAgo', { days })
        return date.toLocaleDateString(locale === 'en' ? 'en-US' : 'zh-CN', { month: 'short', day: 'numeric' })
    }

    return (
        <div className="flex flex-col h-full bg-white border-r border-slate-200/60">
            {/* Header */}
            <div className="p-3 border-b border-slate-100/50 flex items-center gap-2">
                <button
                    onClick={onNewChat}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2.5 bg-primary hover:opacity-90 text-white rounded-xl transition-all text-sm font-medium shadow-sm shadow-primary/20"
                >
                    <Plus className="h-4 w-4" />
                    {t('newChat')}
                </button>
                <button
                    onClick={onToggle}
                    className="p-2.5 text-slate-400 hover:text-slate-600 hover:bg-slate-50 rounded-xl transition-all"
                    title={t('hideSidebar')}
                >
                    <PanelLeftClose className="h-4 w-4" />
                </button>
            </div>

            {/* Conversation list */}
            <div className="flex-1 overflow-y-auto">
                {loading ? (
                    <div className="p-4 text-center text-slate-400 text-sm">{t('noConversations')}</div>
                ) : conversations.length === 0 ? (
                    <div className="p-4 text-center text-slate-400 text-sm">{t('noConversations')}</div>
                ) : (
                    <div className="py-2 px-2">
                        {conversations.map((conv) => (
                            <div
                                key={conv.id}
                                onClick={() => onSelect(conv.id)}
                                className={`group relative mb-1 px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-200 ${activeId === conv.id
                                    ? 'bg-primary/5 text-primary'
                                    : 'hover:bg-slate-50 text-slate-600 hover:text-slate-900'
                                    }`}
                            >
                                <div className="flex items-center gap-2 overflow-hidden">
                                    <MessageSquare className={`h-4 w-4 flex-shrink-0 ${activeId === conv.id ? 'text-primary' : 'text-slate-400'}`} />
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium truncate leading-tight">{conv.title}</p>
                                        <p className="text-[10px] text-slate-400 mt-1 uppercase tracking-wider">{formatDate(conv.updated_at)}</p>
                                    </div>

                                    {/* Direct Delete Button on Hover */}
                                    <button
                                        onClick={(e) => handleDelete(conv.id, e)}
                                        disabled={deletingId === conv.id}
                                        className={`p-1.5 rounded-md text-slate-400 hover:text-red-600 hover:bg-red-50 transition-all opacity-0 group-hover:opacity-100 ${deletingId === conv.id ? 'cursor-not-allowed' : ''
                                            }`}
                                        title={t('deleteChat')}
                                    >
                                        {deletingId === conv.id ? (
                                            <div className="h-4 w-4 border-2 border-slate-300 border-t-slate-500 rounded-full animate-spin" />
                                        ) : (
                                            <Trash2 className="h-4 w-4" />
                                        )}
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}
