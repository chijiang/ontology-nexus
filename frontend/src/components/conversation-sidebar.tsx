// frontend/src/components/conversation-sidebar.tsx
'use client'

import { useState, useEffect } from 'react'
import { conversationApi, Conversation } from '@/lib/api'
import { Plus, MessageSquare, Trash2, PanelLeftClose } from 'lucide-react'

interface ConversationSidebarProps {
    activeId: number | null
    onSelect: (id: number | null) => void
    onNewChat: () => void
    onToggle: () => void
}

export function ConversationSidebar({ activeId, onSelect, onNewChat, onToggle }: ConversationSidebarProps) {
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

        if (!confirm('确定要删除这段对话吗？')) return

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

        if (days === 0) return '今天'
        if (days === 1) return '昨天'
        if (days < 7) return `${days}天前`
        return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
    }

    return (
        <div className="flex flex-col h-full bg-slate-50 border-r border-slate-200">
            {/* Header */}
            <div className="p-3 border-b border-slate-200 flex items-center gap-2">
                <button
                    onClick={onNewChat}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors text-sm font-medium shadow-sm"
                >
                    <Plus className="h-4 w-4" />
                    新对话
                </button>
                <button
                    onClick={onToggle}
                    className="p-2.5 text-slate-500 hover:bg-slate-200 rounded-lg transition-colors"
                    title="隐藏侧边栏"
                >
                    <PanelLeftClose className="h-4 w-4" />
                </button>
            </div>

            {/* Conversation list */}
            <div className="flex-1 overflow-y-auto">
                {loading ? (
                    <div className="p-4 text-center text-slate-400 text-sm">加载中...</div>
                ) : conversations.length === 0 ? (
                    <div className="p-4 text-center text-slate-400 text-sm">暂无对话</div>
                ) : (
                    <div className="py-2 px-2">
                        {conversations.map((conv) => (
                            <div
                                key={conv.id}
                                onClick={() => onSelect(conv.id)}
                                className={`group relative mb-1 px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-200 ${activeId === conv.id
                                    ? 'bg-indigo-100 text-indigo-900 ring-1 ring-indigo-200'
                                    : 'hover:bg-slate-200 hover:shadow-sm text-slate-700'
                                    }`}
                            >
                                <div className="flex items-center gap-2 overflow-hidden">
                                    <MessageSquare className={`h-4 w-4 flex-shrink-0 ${activeId === conv.id ? 'text-indigo-600' : 'text-slate-400'}`} />
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
                                        title="删除对话"
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
