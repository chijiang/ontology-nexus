// frontend/src/components/thinking-process.tsx
import { Sparkles, Wrench, Brain, Terminal, Info } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useTranslations } from 'next-intl'

interface ThinkingProcessProps {
    content: string
}

export function ThinkingProcess({ content }: ThinkingProcessProps) {
    const t = useTranslations('components')
    // Split by " > " or "\n\n> " or just "> "
    const steps = content.split(/\n?\s*>\s*/g).filter((s) => s.trim().length > 0)

    return (
        <div className="flex flex-col gap-3 py-1">
            {steps.map((step, index) => {
                const isToolCall = step.includes('**Calling tool**:')
                const toolMatch = step.match(/\*\*Calling tool\*\*:\s*`([^`]+)`/)
                const toolName = toolMatch ? toolMatch[1] : ''

                // Remove the tool call header from the step content to avoid double rendering
                let cleanContent = step
                if (toolMatch) {
                    cleanContent = step.replace(/\*\*Calling tool\*\*:\s*`[^`]+`/, '').trim()
                }

                return (
                    <div key={index} className="flex gap-3 group">
                        {/* Timeline connector */}
                        <div className="flex flex-col items-center">
                            <div className={`mt-1 flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center border ${isToolCall ? 'bg-orange-50 border-orange-200 text-orange-600' : 'bg-primary/5 border-primary/20 text-primary'
                                }`}>
                                {isToolCall ? <Wrench className="h-3.5 w-3.5" /> : <Brain className="h-3.5 w-3.5" />}
                            </div>
                            {index < steps.length - 1 && (
                                <div className="w-px flex-1 bg-slate-200 my-1 group-last:hidden" />
                            )}
                        </div>

                        {/* Step content */}
                        <div className="flex-1 pb-2">
                            <div className="flex items-center gap-2 mb-1">
                                <span className={`text-[11px] font-semibold uppercase tracking-wider ${isToolCall ? 'text-orange-700' : 'text-primary/80'
                                    }`}>
                                    {isToolCall ? t('thinkingProcess.action', { toolName }) : t('thinkingProcess.thought')}
                                </span>
                                {index === steps.length - 1 && (
                                    <span className="flex h-1.5 w-1.5 rounded-full bg-primary/50 animate-pulse" />
                                )}
                            </div>

                            <div className="prose prose-sm max-w-none text-[12px] text-slate-600 prose-code:bg-slate-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-orange-600 prose-pre:bg-slate-900 prose-pre:text-slate-100 prose-pre:border-none prose-pre:p-3 prose-pre:rounded-lg">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {cleanContent || '...'}
                                </ReactMarkdown>
                            </div>
                        </div>
                    </div>
                )
            })}
        </div>
    )
}
