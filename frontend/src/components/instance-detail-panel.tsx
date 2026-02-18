// frontend/src/components/instance-detail-panel.tsx
'use client'

import { useState, useEffect } from 'react'
import { graphApi, actionsApi, ActionRuntimeInfo } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { X, Save, Edit2, Check, XCircle, Play, Loader2, Plus, Info, Zap, ChevronRight, ChevronDown, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { useTranslations } from 'next-intl'
import { cn } from '@/lib/utils'

interface InstanceNode {
    id: string
    name: string
    label: string
    nodeLabel: string
    labels?: string[]
    aliases?: string[]
    properties?: Record<string, any>
    color?: string
}

interface InstanceDetailPanelProps {
    node: InstanceNode | null
    onClose: () => void
    onUpdate?: () => void
}

export function InstanceDetailPanel({ node, onClose, onUpdate }: InstanceDetailPanelProps) {
    const t = useTranslations()
    const token = useAuthStore((state) => state.token)
    const [editing, setEditing] = useState(false)
    const [editedProperties, setEditedProperties] = useState<Record<string, any>>({})
    const [editingAliases, setEditingAliases] = useState<string[]>([])
    const [originalAliases, setOriginalAliases] = useState<string[]>([])
    const [saving, setSaving] = useState(false)
    const [metadata, setMetadata] = useState<Record<string, any>>({})
    const [expandedProps, setExpandedProps] = useState<Record<string, any>>({})
    const [actions, setActions] = useState<ActionRuntimeInfo[]>([])
    const [executingAction, setExecutingAction] = useState<string | null>(null)
    const [actionParams, setActionParams] = useState<Record<string, Record<string, any>>>({})

    // Collapsible sections state
    const [propsOpen, setPropsOpen] = useState(true)
    const [actionsOpen, setActionsOpen] = useState(true)

    useEffect(() => {
        if (node) {
            setEditing(false)
            loadNodeDetails()
            loadActions()
        }
    }, [node])

    const loadNodeDetails = async () => {
        if (!node || !token) return

        try {
            const res = await graphApi.getNode(node.id || node.name, token)
            const data = res.data || {}

            setMetadata({
                ID: data.id,
                NAME: data.name,
                TYPE: data.entity_type
            })

            const props = data.properties || {}
            const filteredProps: Record<string, any> = {}
            Object.entries(props).forEach(([key, value]) => {
                if (!key.startsWith('__') && key !== 'id') {
                    filteredProps[key] = value
                }
            })
            setExpandedProps(filteredProps)
            setEditedProperties(filteredProps)
            const aliases = data.aliases || []
            setEditingAliases(aliases)
            setOriginalAliases(aliases)
        } catch (err) {
            console.error('Failed to load node details:', err)
            setMetadata({
                NAME: node.name,
                TYPE: node.nodeLabel
            })
            const props = node.properties || {}
            setExpandedProps(props)
            setEditedProperties(props)
            setEditingAliases(node.aliases || [])
        }
    }

    const handleStartEdit = () => {
        setEditing(true)
        setEditedProperties({ ...expandedProps })
        setEditingAliases([...editingAliases])
    }

    const handleCancelEdit = () => {
        setEditing(false)
        setEditedProperties({ ...expandedProps })
        setEditingAliases([...editingAliases])
    }

    const handlePropertyChange = (key: string, value: any) => {
        setEditedProperties({
            ...editedProperties,
            [key]: value
        })
    }

    const handleSave = async () => {
        if (!node || !token) return

        setSaving(true)
        try {
            const updates: Record<string, any> = {}
            Object.entries(editedProperties).forEach(([key, value]) => {
                if (expandedProps[key] !== value) {
                    updates[key] = value
                }
            })

            const filteredEditingAliases = editingAliases.filter(a => a.trim() !== '')
            if (JSON.stringify(filteredEditingAliases) !== JSON.stringify(originalAliases)) {
                updates['__aliases__'] = filteredEditingAliases
            }

            if (Object.keys(updates).length === 0) {
                toast.info(t('components.instance.noChanges'))
                setEditing(false)
                return
            }

            await graphApi.updateEntity(node.nodeLabel, node.name, updates, token)
            toast.success(t('components.instance.propertiesUpdated'))
            setExpandedProps({ ...editedProperties })
            setOriginalAliases([...editingAliases])
            setEditing(false)
            onUpdate?.()
        } catch (err: any) {
            console.error('Failed to update entity:', err)
            toast.error(err.response?.data?.detail || t('components.instance.updateFailed'))
        } finally {
            setSaving(false)
        }
    }

    const loadActions = async () => {
        if (!node || !token) return

        try {
            const labels = node.labels || [node.nodeLabel]
            const allActions: any[] = []

            for (const label of labels) {
                const res = await actionsApi.listByEntityType(label)
                if (res.data?.actions) {
                    allActions.push(...res.data.actions)
                }
            }

            const uniqueActions = Array.from(new Map(allActions.map(a => [`${a.entity_type}.${a.action_name}`, a])).values()) as ActionRuntimeInfo[]
            setActions(uniqueActions)
        } catch (err) {
            console.error('Failed to load actions:', err)
            setActions([])
        }
    }

    const handleExecuteAction = async (action: any) => {
        if (!node || !token) return

        const actionKey = `${action.entity_type}.${action.action_name}`
        setExecutingAction(actionKey)

        try {
            const params = actionParams[actionKey] || {}
            const res = await actionsApi.execute(
                action.entity_type,
                action.action_name,
                node.name,
                expandedProps,
                params
            )

            if (res.data?.success) {
                toast.success(res.data.message || t('components.instance.actionSuccess'))
                loadNodeDetails()
                onUpdate?.()
            } else {
                toast.warning(res.data?.message || res.data?.detail || t('components.instance.actionFailed'))
            }
        } catch (err: any) {
            const errorMessage = err.response?.data?.detail || err.message || t('components.instance.actionExecutionFailed')
            toast.error(errorMessage)
        } finally {
            setExecutingAction(null)
        }
    }

    if (!node) {
        return (
            <div className="bg-white rounded-lg border h-full flex items-center justify-center p-6 text-center text-slate-400">
                <div className="flex flex-col items-center gap-2">
                    <Info className="h-8 w-8 text-slate-200" />
                    <p className="text-sm">{t('components.instance.selectNodeHint') || '请选择一个节点查看详情'}</p>
                </div>
            </div>
        )
    }

    const displayProps = editing ? editedProperties : expandedProps

    return (
        <div className="bg-white rounded-lg shadow-sm border h-full flex flex-col font-sans">
            {/* 头部 */}
            <div className="px-3 py-2.5 border-b flex items-center justify-between bg-slate-50/50">
                <div className="flex items-center gap-2 min-w-0">
                    <div
                        className="w-5 h-5 rounded-full flex items-center justify-center text-white text-[9px] font-bold flex-shrink-0"
                        style={{ backgroundColor: node.color || '#4C8EDA' }}
                    >
                        {node.nodeLabel?.charAt(0) || 'E'}
                    </div>
                    <div className="min-w-0">
                        <h3 className="text-sm font-semibold text-slate-800 truncate leading-tight">{node.name}</h3>
                    </div>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                    {!editing ? (
                        <Button variant="ghost" size="sm" className="h-6 w-6 p-0 hover:bg-slate-200" onClick={handleStartEdit}>
                            <Edit2 className="h-3.5 w-3.5 text-slate-500" />
                        </Button>
                    ) : (
                        <>
                            <Button variant="ghost" size="sm" className="h-6 w-6 p-0 hover:bg-red-100" onClick={handleCancelEdit}>
                                <XCircle className="h-3.5 w-3.5 text-red-500" />
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 w-6 p-0 hover:bg-green-100"
                                onClick={handleSave}
                                disabled={saving}
                            >
                                {saving ? (
                                    <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-green-600" />
                                ) : (
                                    <Check className="h-3.5 w-3.5 text-green-600" />
                                )}
                            </Button>
                        </>
                    )}
                    <button
                        onClick={onClose}
                        className="h-6 w-6 flex items-center justify-center hover:bg-slate-200 rounded transition-colors"
                    >
                        <X className="h-3.5 w-3.5 text-slate-400" />
                    </button>
                </div>
            </div>

            {/* 内容区域 */}
            <div className="flex-1 overflow-y-auto custom-scrollbar">
                {/* 元数据 Badge */}
                <div className="px-3 py-2 flex flex-wrap gap-1.5 border-b border-slate-50">
                    <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-100 text-slate-500 border border-slate-200">
                        {node.nodeLabel}
                    </span>
                    {metadata.ID && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-50 text-slate-400 border border-slate-100">
                            ID: {metadata.ID}
                        </span>
                    )}
                </div>

                {/* 别名 */}
                {(editing || editingAliases.length > 0) && (
                    <div className="px-3 py-2 border-b border-slate-50">
                        <span className="text-[10px] font-bold text-slate-400 tracking-wider uppercase mb-1.5 block">{t('components.instance.aliases')}</span>
                        {editing ? (
                            <div className="flex flex-col gap-1.5">
                                {editingAliases.map((a, i) => (
                                    <div key={i} className="flex gap-1 items-center">
                                        <Input
                                            value={a}
                                            onChange={(e) => {
                                                const newAliases = [...editingAliases]
                                                newAliases[i] = e.target.value
                                                setEditingAliases(newAliases)
                                            }}
                                            className="h-6 text-xs px-2"
                                            placeholder={t('components.instance.aliases')}
                                        />
                                        <button onClick={() => setEditingAliases(editingAliases.filter((_, idx) => idx !== i))} className="text-slate-400 hover:text-red-500">
                                            <X className="h-3 w-3" />
                                        </button>
                                    </div>
                                ))}
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-5 text-[10px] w-fit px-0 text-primary hover:bg-transparent hover:text-primary/80"
                                    onClick={() => setEditingAliases([...editingAliases, ''])}
                                >
                                    <Plus className="h-3 w-3 mr-1" /> {t('components.instance.addAlias')}
                                </Button>
                            </div>
                        ) : (
                            <div className="flex flex-wrap gap-1">
                                {editingAliases.map((a, i) => (
                                    <span key={i} className="text-[10px] bg-slate-50 text-slate-600 px-1.5 py-0.5 rounded border border-slate-100">
                                        {a}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* 属性列表 */}
                <div className="py-1">
                    <button
                        className="w-full flex items-center justify-between px-3 py-1.5 hover:bg-slate-50 transition-colors"
                        onClick={() => setPropsOpen(!propsOpen)}
                    >
                        <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wide flex items-center gap-1.5">
                            <div className="w-1 h-3 bg-blue-400 rounded-full" />
                            {t('components.instance.businessProperties')}
                        </h4>
                        {propsOpen ? <ChevronDown className="h-3 w-3 text-slate-400" /> : <ChevronRight className="h-3 w-3 text-slate-400" />}
                    </button>

                    {propsOpen && (
                        <div className="px-3 py-1 space-y-0.5">
                            {Object.keys(displayProps).length === 0 ? (
                                <p className="text-[10px] text-slate-400 italic py-1 pl-2">{t('components.instance.noProperties')}</p>
                            ) : (
                                Object.entries(displayProps).map(([key, value]) => (
                                    <div key={key} className="group flex items-center justify-between py-1 border-b border-dashed border-slate-100 last:border-0 hover:bg-slate-50/80 rounded px-1 -mx-1">
                                        <span className="text-[11px] font-medium text-slate-500 min-w-[30%] truncate pr-2" title={key}>
                                            {key}
                                        </span>
                                        {editing ? (
                                            <Input
                                                value={String(value ?? '')}
                                                onChange={(e) => handlePropertyChange(key, e.target.value)}
                                                className="h-6 text-xs bg-white text-right w-full border-slate-200 focus-visible:ring-1"
                                            />
                                        ) : (
                                            <span className="text-[11px] text-slate-700 truncate text-right font-mono" title={String(value)}>
                                                {formatValue(value, t)}
                                            </span>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    )}
                </div>

                {/* 可用操作 */}
                {actions.length > 0 && (
                    <div className="py-1 border-t border-slate-50 mt-1">
                        <button
                            className="w-full flex items-center justify-between px-3 py-1.5 hover:bg-slate-50 transition-colors"
                            onClick={() => setActionsOpen(!actionsOpen)}
                        >
                            <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wide flex items-center gap-1.5">
                                <div className="w-1 h-3 bg-purple-400 rounded-full" />
                                {t('components.instance.availableActions')}
                            </h4>
                            {actionsOpen ? <ChevronDown className="h-3 w-3 text-slate-400" /> : <ChevronRight className="h-3 w-3 text-slate-400" />}
                        </button>

                        {actionsOpen && (
                            <div className="px-3 py-1 space-y-2">
                                {actions.map((action) => {
                                    const actionKey = `${action.entity_type}.${action.action_name}`
                                    const isExecuting = executingAction === actionKey

                                    return (
                                        <div key={actionKey} className="border rounded bg-slate-50/30 p-2 space-y-2">
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-1.5">
                                                    <Zap className="h-3 w-3 text-purple-500 fill-purple-500/10" />
                                                    <span className="text-xs font-medium text-slate-700">{action.action_name}</span>
                                                    {action.has_call && (
                                                        <span className="text-[9px] bg-blue-50 text-blue-600 px-1 py-px rounded border border-blue-100">RPC</span>
                                                    )}
                                                </div>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="h-5 text-[10px] px-2 text-purple-600 hover:text-purple-700 hover:bg-purple-50"
                                                    onClick={() => handleExecuteAction(action)}
                                                    disabled={!!executingAction}
                                                >
                                                    {isExecuting ? (
                                                        <Loader2 className="h-3 w-3 animate-spin" />
                                                    ) : (
                                                        <Play className="h-3 w-3" />
                                                    )}
                                                    <span className="ml-1">{t('components.instance.execute')}</span>
                                                </Button>
                                            </div>

                                            {action.parameters && action.parameters.length > 0 && (
                                                <div className="space-y-1.5 bg-white rounded border border-slate-100 p-1.5">
                                                    {action.parameters.map((param) => (
                                                        <div key={param.name} className="flex items-center gap-2">
                                                            <span className="text-[10px] text-slate-400 uppercase w-12 flex-shrink-0 text-right">{param.name}</span>
                                                            <Input
                                                                className="h-5 text-[10px] bg-slate-50 border-slate-100 px-1.5"
                                                                placeholder={param.type}
                                                                value={actionParams[actionKey]?.[param.name] ?? ''}
                                                                onChange={(e) => setActionParams({
                                                                    ...actionParams,
                                                                    [actionKey]: {
                                                                        ...(actionParams[actionKey] || {}),
                                                                        [param.name]: param.type === 'number' ? Number(e.target.value) : e.target.value
                                                                    }
                                                                })}
                                                            />
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )
                                })}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    )
}

function formatValue(value: any, t: any): string {
    if (value === null || value === undefined) return '-'
    if (typeof value === 'boolean') return value ? (t('components.instance.yes') || 'Yes') : (t('components.instance.no') || 'No')
    if (Array.isArray(value)) return value.join(', ')
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
}
