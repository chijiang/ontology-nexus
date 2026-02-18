// frontend/src/components/chat.tsx
'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { chatApi, conversationApi, Message as ApiMessage } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { Send, Bot, User, Sparkles, ChevronDown, ChevronUp, ListTodo } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useTranslations } from 'next-intl'
import { ThinkingProcess } from './thinking-process'


// ... (skipping interfaces) ...

// Inside Chat function:
// Remove internal mode state

interface Message {
  role: 'user' | 'assistant'
  content: string
  thinking?: string
  graphData?: any
}

interface ChatProps {
  onGraphData: (data: any) => void
  conversationId: number | null
  initialMessages: ApiMessage[]
  onConversationCreated: (id: number) => void
  mode: 'llm' | 'non-llm'
  onModeChange: (mode: 'llm' | 'non-llm') => void
}

export function Chat({ onGraphData, conversationId, initialMessages, onConversationCreated, mode, onModeChange }: ChatProps) {
  const t = useTranslations('components.chat')
  const token = useAuthStore((state) => state.token)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [expandedThinking, setExpandedThinking] = useState<number | null>(null)
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(conversationId)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const hasGeneratedTitle = useRef(false)

  // 初始化消息
  useEffect(() => {
    // 如果当前的 ID 已经匹配且消息不为空，说明是刚创建的对话并正在流式传输，不要重置
    if (conversationId !== null && conversationId === currentConversationId && messages.length > 0) {
      return
    }

    const msgs: Message[] = initialMessages.map(m => ({
      role: m.role,
      content: m.content,
      thinking: m.extra_metadata?.thinking,
      graphData: m.extra_metadata?.graph_data
    }))
    setMessages(msgs)
    setCurrentConversationId(conversationId)
    hasGeneratedTitle.current = conversationId !== null
  }, [initialMessages, conversationId])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = input
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    try {
      const response = await chatApi.stream(userMessage, token!, currentConversationId || undefined, mode)
      const reader = response.body!.getReader()
      const decoder = new TextDecoder()

      let assistantMessage = ''
      let thinking = ''
      let newConversationId = currentConversationId

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n').filter(Boolean)

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))

            if (data.type === 'thinking') {
              thinking += data.content
              if (data.conversation_id) {
                newConversationId = data.conversation_id
                setCurrentConversationId(data.conversation_id)
              }
              setMessages((prev) => {
                const newMsgs = [...prev]
                const last = newMsgs[newMsgs.length - 1]
                if (last?.role === 'assistant') {
                  last.thinking = thinking
                } else {
                  newMsgs.push({ role: 'assistant', content: '', thinking })
                }
                return newMsgs
              })
            } else if (data.type === 'content') {
              assistantMessage += data.content
              setMessages((prev) => {
                const newMsgs = [...prev]
                const last = newMsgs[newMsgs.length - 1]
                if (last?.role === 'assistant') {
                  last.content = assistantMessage
                } else {
                  newMsgs.push({ role: 'assistant', content: assistantMessage })
                }
                return newMsgs
              })
            } else if (data.type === 'graph_data') {
              const graphData = { nodes: data.nodes || [], edges: data.edges || [] }
              onGraphData(graphData)
              setMessages((prev) => {
                const newMsgs = [...prev]
                const last = newMsgs[newMsgs.length - 1]
                if (last) {
                  last.graphData = graphData
                }
                return newMsgs
              })
            } else if (data.type === 'conversation_id') {
              newConversationId = data.id
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', e)
          }
        }
      }

      // 更新对话 ID
      if (newConversationId && newConversationId !== currentConversationId) {
        setCurrentConversationId(newConversationId)
        onConversationCreated(newConversationId)

        // 生成标题
        if (!hasGeneratedTitle.current) {
          hasGeneratedTitle.current = true
          try {
            await conversationApi.generateTitle(newConversationId)
          } catch (err) {
            console.error('Failed to generate title:', err)
          }
        }
      }
    } catch (err) {
      console.error('Chat error:', err)
      setMessages((prev) => [...prev, { role: 'assistant', content: t('error') }])
    } finally {
      setLoading(false)
    }
  }

  const exampleQuestions = mode === 'llm' ? [
    t('exampleQ1'),
    t('exampleQ2'),
    t('exampleQ3')
  ] : [
    t('exampleNonLlm1'),
    t('exampleNonLlm2'),
    t('exampleNonLlm3'),
    t('exampleNonLlm4')
  ]

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className={`p-4 rounded-full mb-4 ${mode === 'llm' ? 'bg-primary/10' : 'bg-orange-100'}`}>
              {mode === 'llm' ? (
                <Sparkles className="h-8 w-8 text-primary" />
              ) : (
                <ListTodo className="h-8 w-8 text-orange-500" />
              )}
            </div>
            <h3 className="text-lg font-medium text-slate-700 mb-2">
              {mode === 'llm' ? t('startExploring') : t('preciseMode')}
            </h3>
            <p className="text-sm text-slate-500 mb-6">
              {mode === 'llm' ? t('tryQuestions') : t('trySpecificInstructions')}
            </p>
            <div className="space-y-2 w-full max-w-md">
              {exampleQuestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => setInput(q)}
                  className="w-full px-4 py-3 text-left text-sm bg-white hover:bg-primary/5 border border-slate-200 rounded-lg transition-all hover:border-primary/30 hover:shadow-sm"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
          >
            {/* Avatar */}
            <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${msg.role === 'user' ? 'bg-primary' : 'bg-slate-800'
              }`}>
              {msg.role === 'user' ? (
                <User className="h-4 w-4 text-white" />
              ) : (
                <Bot className="h-4 w-4 text-white" />
              )}
            </div>

            {/* Message bubble */}
            <div className={`max-w-[80%] min-w-0 break-words ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              {/* Thinking panel */}
              {msg.thinking && (
                <button
                  onClick={() => setExpandedThinking(expandedThinking === i ? null : i)}
                  className="flex items-center gap-1 text-xs text-slate-500 mb-1 hover:text-primary transition-colors"
                >
                  <Sparkles className="h-3 w-3" />
                  <span>{t('thinking')}</span>
                  {expandedThinking === i ? (
                    <ChevronUp className="h-3 w-3" />
                  ) : (
                    <ChevronDown className="h-3 w-3" />
                  )}
                </button>
              )}
              {expandedThinking === i && msg.thinking && (
                <div className="mb-3 px-4 py-3 bg-slate-50/50 rounded-xl border border-slate-100 shadow-sm">
                  <ThinkingProcess content={msg.thinking} />
                </div>
              )}

              {/* Main content */}
              <div className={`px-4 py-3 rounded-lg ${msg.role === 'user'
                ? 'bg-primary text-white rounded-tr-none'
                : 'bg-slate-100 text-slate-700 rounded-tl-none'
                }`}>
                {msg.role === 'user' ? (
                  <p className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>
                ) : (
                  <div className="prose max-w-none text-[13px] text-slate-700 prose-slate prose-headings:font-semibold prose-headings:text-slate-800 prose-p:leading-relaxed prose-li:my-1 prose-table:border prose-table:border-slate-200 prose-th:bg-slate-50 prose-th:px-2 prose-th:py-1 prose-td:px-2 prose-td:py-1 overflow-x-auto min-w-0">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content || '...'}
                    </ReactMarkdown>
                  </div>
                )}
              </div>

              {/* Graph indicator */}
              {msg.graphData && (
                <div className="flex items-center gap-1.5 mt-2 px-2.5 py-1 bg-primary/10 text-primary border border-primary/20 rounded-full text-xs w-fit font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                  {t('previewUpdated')}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {loading && (
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center">
              <Bot className="h-4 w-4 text-white" />
            </div>
            <div className="px-4 py-3 bg-slate-100 rounded-lg rounded-tl-none">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="p-4 border-t border-slate-100 bg-white">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={t('placeholder')}
            disabled={loading}
            className="flex-1 px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all placeholder:text-slate-400"
          />
          <Button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-3 bg-primary hover:opacity-90 text-white rounded-lg transition-all disabled:opacity-50"
            title={t('send')}
          >
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </div>
  )
}
