// frontend/src/app/graph/ontology/page.tsx
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { AppLayout } from '@/components/layout'
import { SchemaViewer } from '@/components/schema-viewer'
import { OntologyDetailPanel } from '@/components/ontology-detail-panel'
import { useAuthStore } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { Download, Loader2, Edit3, Eye, Plus, Info, ArrowRight } from 'lucide-react'
import { toast } from 'sonner'
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { graphApi } from '@/lib/api'

export interface OntologyNode {
    name: string
    label?: string
    dataProperties?: string[]
    color?: string
}

export type Selection =
    | { type: 'node'; data: OntologyNode }
    | { type: 'edge'; data: { source: string; target: string; relationship_type: string } }

export default function OntologyPage() {
    const router = useRouter()
    const t = useTranslations()
    const token = useAuthStore((state) => state.token)
    const [isHydrated, setIsHydrated] = useState(false)
    const [selection, setSelection] = useState<Selection | null>(null)
    const [isExporting, setIsExporting] = useState(false)
    const [isEditMode, setIsEditMode] = useState(false)
    const [refreshKey, setRefreshKey] = useState(0)

    // Add Class Modal State
    const [isAddClassOpen, setIsAddClassOpen] = useState(false)
    const [newClassName, setNewClassName] = useState('')
    const [isCreatingClass, setIsCreatingClass] = useState(false)

    // Add Relationship Workflow State
    const [relStep, setRelStep] = useState<'IDLE' | 'SOURCE' | 'TARGET' | 'TYPE'>('IDLE')
    const [relSource, setRelSource] = useState<string | null>(null)
    const [relTarget, setRelTarget] = useState<string | null>(null)
    const [relType, setRelType] = useState('')
    const [isCreatingRel, setIsCreatingRel] = useState(false)

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

    const handleExport = async () => {
        setIsExporting(true)
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/graph/export/ontology`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })

            if (!response.ok) {
                throw new Error('Export failed')
            }

            const blob = await response.blob()
            const url = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = 'ontology.ttl'
            document.body.appendChild(a)
            a.click()
            window.URL.revokeObjectURL(url)
            document.body.removeChild(a)
            toast.success(t('graph.ontology.exportSuccess'))
        } catch (error) {
            console.error('Export error:', error)
            toast.error(t('graph.ontology.exportFailed'))
        } finally {
            setIsExporting(false)
        }
    }

    const handleAddClass = async () => {
        if (!newClassName.trim()) return
        setIsCreatingClass(true)
        try {
            await graphApi.addClass(newClassName.trim(), newClassName.trim())
            toast.success(t('graph.ontology.classAdded', { name: newClassName }))
            setIsAddClassOpen(false)
            setNewClassName('')
            setRefreshKey(prev => prev + 1)
        } catch (err: any) {
            toast.error(`${t('graph.ontology.addFailed')}: ${err.response?.data?.detail || err.message}`)
        } finally {
            setIsCreatingClass(false)
        }
    }

    const startAddRel = () => {
        setRelStep('SOURCE')
        setRelSource(null)
        setRelTarget(null)
        setSelection(null)
        toast.info(t('graph.ontology.clickSource'), { duration: 5000 })
    }

    const handleRelCreation = async () => {
        if (!relSource || !relTarget || !relType.trim()) return
        setIsCreatingRel(true)
        try {
            await graphApi.addRelationship(relSource, relType.trim(), relTarget)
            toast.success(t('graph.ontology.relationshipAdded'))
            setRelStep('IDLE')
            setRelType('')
            setRefreshKey(prev => prev + 1)
        } catch (err: any) {
            toast.error(`${t('graph.ontology.addFailed')}: ${err.response?.data?.detail || err.message}`)
        } finally {
            setIsCreatingRel(false)
        }
    }

    const cancelRelCreation = () => {
        setRelStep('IDLE')
        setRelSource(null)
        setRelTarget(null)
        toast(t('graph.ontology.creationCancelled'))
    }

    return (
        <AppLayout>
            <div className="flex flex-col h-[calc(100vh-120px)] gap-3">
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <h2 className="text-lg font-semibold text-slate-800">{t('graph.ontology.title')}</h2>
                        {isEditMode && relStep !== 'IDLE' && (
                            <div className="flex items-center gap-1.5 bg-blue-50 px-2.5 py-1 rounded-md border border-blue-200 text-blue-600 text-xs">
                                <Info className="w-3 h-3" />
                                <span>
                                    {relStep === 'SOURCE' && t('graph.ontology.stepSource')}
                                    {relStep === 'TARGET' && t('graph.ontology.stepTarget')}
                                    {relStep === 'TYPE' && t('graph.ontology.stepType')}
                                </span>
                                <button onClick={cancelRelCreation} className="ml-1 text-blue-500 hover:text-blue-700 text-xs underline">{t('common.cancel')}</button>
                            </div>
                        )}
                    </div>
                    <div className="flex gap-1.5">
                        {isEditMode && relStep === 'IDLE' && (
                            <>
                                <Button
                                    size="sm"
                                    variant="outline"
                                    className="h-7 text-xs border-green-200 text-green-700 hover:bg-green-50"
                                    onClick={() => setIsAddClassOpen(true)}
                                >
                                    <Plus className="w-3 h-3 mr-1" />
                                    {t('graph.ontology.addClass')}
                                </Button>
                                <Button
                                    size="sm"
                                    variant="outline"
                                    className="h-7 text-xs border-blue-200 text-blue-700 hover:bg-blue-50"
                                    onClick={startAddRel}
                                >
                                    <Plus className="w-3 h-3 mr-1" />
                                    {t('graph.ontology.addRelationship')}
                                </Button>
                            </>
                        )}
                        <Button
                            size="sm"
                            variant={isEditMode ? "default" : "outline"}
                            onClick={() => {
                                setIsEditMode(!isEditMode)
                                setRelStep('IDLE')
                            }}
                            className={`h-7 text-xs ${isEditMode ? "bg-amber-500 hover:bg-amber-600 border-none" : "border-slate-200"}`}
                        >
                            {isEditMode ? <Eye className="w-3 h-3 mr-1" /> : <Edit3 className="w-3 h-3 mr-1" />}
                            {isEditMode ? t('graph.ontology.exitEditMode') : t('graph.ontology.editMode')}
                        </Button>
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={handleExport}
                            disabled={isExporting}
                            className="h-7 text-xs border-slate-200"
                        >
                            {isExporting ? (
                                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                            ) : (
                                <Download className="w-3 h-3 mr-1" />
                            )}
                            {t('graph.ontology.exportTTL')}
                        </Button>
                    </div>
                </div>
                <div className="flex-1 min-h-0">
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 h-full">
                        {/* Left: Ontology Graph */}
                        <div className={`bg-white rounded-lg border border-slate-200 overflow-hidden ${selection ? 'lg:col-span-2' : 'lg:col-span-3'}`}>
                            <SchemaViewer
                                key={refreshKey}
                                isEditMode={isEditMode}
                                activeStep={relStep}
                                sourceNode={relSource}
                                onNodeSelect={(node) => {
                                    if (relStep === 'SOURCE') {
                                        if (node) {
                                            setRelSource(node.name)
                                            setRelStep('TARGET')
                                            toast.info(t('graph.ontology.sourceSelected'))
                                        }
                                    } else if (relStep === 'TARGET') {
                                        if (node) {
                                            if (node.name === relSource) {
                                                toast.error(t('graph.ontology.sourceTargetSame'))
                                                return
                                            }
                                            setRelTarget(node.name)
                                            setRelStep('TYPE')
                                        }
                                    } else {
                                        setSelection(node ? { type: 'node', data: node } : null)
                                    }
                                }}
                                onEdgeSelect={(edge) => {
                                    if (relStep === 'IDLE') {
                                        setSelection(edge ? { type: 'edge', data: edge } : null)
                                    }
                                }}
                                onSchemaChange={() => setRefreshKey(prev => prev + 1)}
                            />
                        </div>

                        {/* Right: Detail Panel */}
                        {selection && (
                            <div className="lg:col-span-1">
                                <OntologyDetailPanel
                                    selection={selection}
                                    isEditMode={isEditMode}
                                    onClose={() => setSelection(null)}
                                    onUpdate={() => setRefreshKey(prev => prev + 1)}
                                />
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Add Class Dialog */}
            <Dialog open={isAddClassOpen} onOpenChange={setIsAddClassOpen}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle className="text-base">{t('graph.ontology.addOntologyClass')}</DialogTitle>
                    </DialogHeader>
                    <div className="py-3 text-left">
                        <Label htmlFor="className" className="text-xs text-slate-500">{t('graph.ontology.className')}</Label>
                        <Input
                            id="className"
                            value={newClassName}
                            onChange={(e) => setNewClassName(e.target.value)}
                            placeholder={t('graph.ontology.classPlaceholder')}
                            autoFocus
                            className="mt-1.5 h-8 text-sm"
                        />
                    </div>
                    <DialogFooter className="gap-2">
                        <Button size="sm" variant="outline" onClick={() => setIsAddClassOpen(false)} className="h-7 text-xs">{t('common.cancel')}</Button>
                        <Button size="sm" onClick={handleAddClass} disabled={isCreatingClass || !newClassName} className="h-7 text-xs">
                            {isCreatingClass && <Loader2 className="w-3 h-3 mr-1 animate-spin" />}
                            {t('graph.ontology.create')}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Add Relationship Dialog */}
            <Dialog open={relStep === 'TYPE'} onOpenChange={(open) => !open && cancelRelCreation()}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle className="text-base">{t('graph.ontology.setRelationshipType')}</DialogTitle>
                    </DialogHeader>
                    <div className="py-3 flex flex-col gap-3 text-left">
                        <div className="flex items-center gap-2 text-xs text-slate-500 bg-slate-50 p-2 rounded justify-center">
                            <span className="font-medium text-slate-700">{relSource}</span>
                            <ArrowRight className="w-3 h-3" />
                            <span className="font-medium text-slate-700">{relTarget}</span>
                        </div>
                        <div>
                            <Label htmlFor="relType" className="text-xs text-slate-500">{t('graph.ontology.relationshipLabel')}</Label>
                            <Input
                                id="relType"
                                value={relType}
                                onChange={(e) => setRelType(e.target.value)}
                                placeholder={t('graph.ontology.relationshipPlaceholder')}
                                autoFocus
                                className="mt-1.5 h-8 text-sm"
                            />
                        </div>
                    </div>
                    <DialogFooter className="gap-2">
                        <Button size="sm" variant="outline" onClick={cancelRelCreation} className="h-7 text-xs">{t('common.cancel')}</Button>
                        <Button size="sm" onClick={handleRelCreation} disabled={isCreatingRel || !relType} className="h-7 text-xs">
                            {isCreatingRel && <Loader2 className="w-3 h-3 mr-1 animate-spin" />}
                            {t('graph.ontology.confirmAdd')}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </AppLayout>
    )
}
