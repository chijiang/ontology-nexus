'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { AppLayout } from '@/components/layout'
import { SchemaViewer } from '@/components/schema-viewer'
import { BindingDetailPanel } from '@/components/binding-detail-panel'
import { useAuthStore } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { Info, Crosshair } from 'lucide-react'
import { toast } from 'sonner'

export interface OntologyNode {
    name: string
    label?: string
    dataProperties?: string[]
    color?: string
}

export type Selection =
    | { type: 'node'; data: OntologyNode }
    | { type: 'edge'; data: { source: string; target: string; relationship_type: string } }

export default function DataBindingPage() {
    const router = useRouter()
    const t = useTranslations()
    const token = useAuthStore((state) => state.token)
    const [isHydrated, setIsHydrated] = useState(false)
    const [selection, setSelection] = useState<Selection | null>(null)
    const [refreshKey, setRefreshKey] = useState(0)

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
            <div className="flex flex-col h-[calc(100vh-120px)] gap-3">
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <h1 className="text-xl font-bold text-slate-800">{t('graph.binding.title')}</h1>
                        <div className="flex items-center gap-1.5 bg-blue-50 px-2.5 py-1 rounded-md border border-blue-200 text-blue-600 text-xs">
                            <Info className="w-3 h-3" />
                            <span>{t('graph.binding.info')}</span>
                        </div>
                    </div>
                </div>

                <div className="flex-1 min-h-0">
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 h-full">
                        {/* Left: Ontology Graph (Read-only) */}
                        <div className={`bg-white rounded-lg border border-slate-200 overflow-hidden ${selection ? 'lg:col-span-2' : 'lg:col-span-3'}`}>
                            <SchemaViewer
                                key={refreshKey}
                                isEditMode={false} // Data binding is read-only for ontology
                                onNodeSelect={(node) => setSelection(node ? { type: 'node', data: node as OntologyNode } : null)}
                                onEdgeSelect={(edge) => setSelection(edge ? { type: 'edge', data: edge } : null)}
                            />
                        </div>

                        {/* Right: Binding Detail Panel */}
                        {selection && (
                            <div className="lg:col-span-1 border-l pl-1 h-full overflow-hidden">
                                <BindingDetailPanel
                                    selection={selection}
                                    onUpdate={() => setRefreshKey(prev => prev + 1)}
                                    onClose={() => setSelection(null)}
                                />
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </AppLayout>
    )
}
