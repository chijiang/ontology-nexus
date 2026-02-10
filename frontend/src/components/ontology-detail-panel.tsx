// frontend/src/components/ontology-detail-panel.tsx
'use client'

import { useEffect, useState } from 'react'
import { graphApi, actionsApi, ActionInfo } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { X, Database, ArrowRight, Zap, Plus, Trash2, Save, Loader2, Palette } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'
import { Label } from '@/components/ui/label'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select'
import { useTranslations } from 'next-intl'

import { Selection, OntologyNode } from '@/app/[locale]/graph/ontology/page'

// Color options for class customization
const COLOR_OPTIONS = [
    '#6366f1', '#8b5cf6', '#a855f7', '#d946ef', '#ec4899',
    '#f43f5e', '#f97316', '#eab308', '#84cc16', '#22c55e',
    '#14b8a6', '#06b6d4', '#0ea5e9', '#3b82f6',
]

interface Relationship {
    source: string
    type: string
    target: string
    direction: 'outgoing' | 'incoming'
}

interface OntologyDetailPanelProps {
    selection: Selection | null
    isEditMode?: boolean
    onUpdate?: () => void
    onClose: () => void
}

export function OntologyDetailPanel({ selection, isEditMode, onUpdate, onClose }: OntologyDetailPanelProps) {
    const t = useTranslations()
    const token = useAuthStore((state) => state.token)
    const [relationships, setRelationships] = useState<Relationship[]>([])
    const [actions, setActions] = useState<ActionInfo[]>([])
    const [loading, setLoading] = useState(false)
    const [editingLabel, setEditingLabel] = useState('')
    const [editingProperties, setEditingProperties] = useState<string[]>([])
    const [editingColor, setEditingColor] = useState<string>('')
    const [isSaving, setIsSaving] = useState(false)
    const [isDeleting, setIsDeleting] = useState(false)
    const [isConfirmDeleting, setIsConfirmDeleting] = useState(false)
    const [showColorPicker, setShowColorPicker] = useState(false)

    // Inline property addition
    const [isAddingProp, setIsAddingProp] = useState(false)
    const [newProp, setNewProp] = useState('')
    const [newPropType, setNewPropType] = useState('string')

    const DATA_TYPES = ['string', 'int', 'float', 'boolean', 'date', 'datetime', 'None']

    // Edge specific state
    const [edgeType, setEdgeType] = useState('')

    const node = selection?.type === 'node' ? selection.data : null
    const edge = selection?.type === 'edge' ? selection.data : null

    useEffect(() => {
        setIsConfirmDeleting(false)
        setShowColorPicker(false)
        if (node && token) {
            loadDetails()
            setEditingLabel(node.label || node.name)
            setEditingProperties(node.dataProperties || [])
            setEditingColor(node.color || '#6366f1')
        } else if (edge) {
            setEdgeType(edge.relationship_type)
        }
    }, [selection, token])

    const loadDetails = async () => {
        if (!node || !token) return
        setLoading(true)

        try {
            const schemaRes = await graphApi.getSchema(token)
            const rels: Relationship[] = []

            schemaRes.data.relationships?.forEach((rel: any) => {
                if (rel.source === node.name) {
                    rels.push({
                        source: rel.source,
                        type: rel.type,
                        target: rel.target,
                        direction: 'outgoing'
                    })
                }
                if (rel.target === node.name) {
                    rels.push({
                        source: rel.source,
                        type: rel.type,
                        target: rel.target,
                        direction: 'incoming'
                    })
                }
            })
            setRelationships(rels)

            try {
                const actionsRes = await actionsApi.list()
                const relatedActions = actionsRes.data.actions?.filter(
                    (action: ActionInfo) => action.entity_type === node.name
                ) || []
                setActions(relatedActions)
            } catch (err) {
                console.error('Failed to load actions:', err)
                setActions([])
            }
        } catch (err) {
            console.error('Failed to load ontology details:', err)
        } finally {
            setLoading(false)
        }
    }

    const handleSaveClass = async () => {
        if (!node) return
        setIsSaving(true)
        try {
            await graphApi.updateClass(node.name, editingLabel, editingProperties, editingColor)
            toast.success(t('common.update') + t('common.success'))
            onUpdate?.()
        } catch (err: any) {
            toast.error(`${t('common.update') + t('common.error')}: ${err.response?.data?.detail || err.message}`)
        } finally {
            setIsSaving(false)
        }
    }

    const handleDeleteNode = async () => {
        if (!node) return
        setIsDeleting(true)
        try {
            await graphApi.deleteClass(node.name)
            toast.success(t('components.ontology.classDeleted'))
            onUpdate?.()
            onClose()
        } catch (err: any) {
            toast.error(`${t('common.delete')}${t('common.error')}: ${err.response?.data?.detail || err.message}`)
        } finally {
            setIsDeleting(false)
            setIsConfirmDeleting(false)
        }
    }

    const handleDeleteEdge = async () => {
        if (!edge) return
        setIsDeleting(true)
        try {
            await graphApi.deleteRelationship(edge.source, edge.relationship_type, edge.target)
            toast.success(t('components.ontology.relationshipDeleted'))
            onUpdate?.()
            onClose()
        } catch (err: any) {
            toast.error(`${t('common.delete')}${t('common.error')}: ${err.response?.data?.detail || err.message}`)
        } finally {
            setIsDeleting(false)
            setIsConfirmDeleting(false)
        }
    }

    const handleConfirmAddProperty = () => {
        if (!newProp.trim()) {
            toast.error(t('components.ontology.enterPropertyName'))
            return
        }
        const fullProp = `${newProp.trim()}:${newPropType}`
        setEditingProperties([...editingProperties, fullProp])
        setNewProp('')
        setNewPropType('string')
        setIsAddingProp(false)
    }

    const handleRemoveProperty = (index: number) => {
        setEditingProperties(editingProperties.filter((_, i) => i !== index))
    }

    const handleRemoveRelationship = async (rel: Relationship) => {
        if (!window.confirm(t('components.ontology.confirmDeleteRelationship', { type: rel.type }))) return
        try {
            await graphApi.deleteRelationship(rel.source, rel.type, rel.target)
            toast.success(t('components.ontology.relationshipDeleted'))
            loadDetails()
            onUpdate?.()
        } catch (err: any) {
            toast.error(`删除失败: ${err.response?.data?.detail || err.message}`)
        }
    }

    if (!selection) return null

    if (edge) {
        return (
            <div className="bg-white rounded-lg border border-slate-200 h-full flex flex-col">
                <div className="px-3 py-2.5 border-b border-slate-100 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded bg-amber-100 flex items-center justify-center">
                            <ArrowRight className="h-3 w-3 text-amber-600" />
                        </div>
                        <div>
                            <h3 className="text-sm font-medium text-slate-700">{t('components.detailPanel.relationship')}</h3>
                            <p className="text-[10px] text-slate-400">{edge.source} → {edge.target}</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded">
                        <X className="h-3.5 w-3.5 text-slate-400" />
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-3 space-y-3">
                    <div className="space-y-2">
                        <div className="flex flex-col gap-0.5">
                            <Label className="text-[10px] text-slate-400">{t('components.ontology.source')}</Label>
                            <div className="px-2 py-1.5 bg-slate-50 rounded text-xs font-medium text-slate-600">{edge.source}</div>
                        </div>
                        <div className="flex flex-col gap-0.5">
                            <Label className="text-[10px] text-slate-400">{t('components.ontology.target')}</Label>
                            <div className="px-2 py-1.5 bg-slate-50 rounded text-xs font-medium text-slate-600">{edge.target}</div>
                        </div>
                        <div className="flex flex-col gap-0.5">
                            <Label className="text-[10px] text-slate-400">{t('common.type')}</Label>
                            <Input
                                value={edgeType}
                                readOnly
                                className="h-7 text-xs bg-slate-50"
                            />
                        </div>
                    </div>
                </div>

                {isEditMode && (
                    <div className="p-3 border-t border-slate-100">
                        {isConfirmDeleting ? (
                            <div className="bg-red-50 p-2 rounded border border-red-100 space-y-2">
                                <p className="text-[10px] text-red-600 text-center">{t('components.ontology.confirmDeleteEdge')}</p>
                                <div className="flex gap-1.5">
                                    <Button
                                        variant="destructive"
                                        size="sm"
                                        className="flex-1 h-6 text-xs"
                                        onClick={handleDeleteEdge}
                                        disabled={isDeleting}
                                    >
                                        {isDeleting && <Loader2 className="h-3 w-3 animate-spin mr-1" />}
                                        {t('common.confirm')}
                                    </Button>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        className="flex-1 h-6 text-xs"
                                        onClick={() => setIsConfirmDeleting(false)}
                                    >
                                        {t('common.cancel')}
                                    </Button>
                                </div>
                            </div>
                        ) : (
                            <Button
                                variant="outline"
                                size="sm"
                                className="w-full h-7 text-xs text-red-500 border-red-200 hover:bg-red-50"
                                onClick={() => setIsConfirmDeleting(true)}
                            >
                                <Trash2 className="h-3 w-3 mr-1" />
                                {t('components.ontology.deleteRelationship')}
                            </Button>
                        )}
                    </div>
                )}
            </div>
        )
    }

    if (!node) return null

    return (
        <div className="bg-white rounded-lg border border-slate-200 h-full flex flex-col">
            {/* Header */}
            <div className="px-3 py-2.5 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <div
                        className="w-6 h-6 rounded flex items-center justify-center"
                        style={{ backgroundColor: editingColor + '20' }}
                    >
                        <Database className="h-3 w-3" style={{ color: editingColor }} />
                    </div>
                    <div className="flex-1 min-w-0">
                        {isEditMode ? (
                            <div className="flex flex-col gap-0.5">
                                <span className="text-[10px] text-slate-400">{node.name}</span>
                                <Input
                                    value={editingLabel}
                                    onChange={(e) => setEditingLabel(e.target.value)}
                                    className="h-6 text-xs py-0 bg-white"
                                    placeholder="标签"
                                />
                            </div>
                        ) : (
                            <>
                                <h3 className="text-sm font-medium text-slate-700 truncate">{node.name}</h3>
                                {node.label && node.label !== node.name && (
                                    <p className="text-[10px] text-slate-400">{node.label}</p>
                                )}
                            </>
                        )}
                    </div>
                </div>
                <div className="flex items-center gap-1">
                    {isEditMode && (
                        <>
                            <Button
                                size="sm"
                                variant="ghost"
                                className="h-6 w-6 p-0"
                                onClick={() => setShowColorPicker(!showColorPicker)}
                                title="选择颜色"
                            >
                                <Palette className="h-3 w-3 text-slate-500" />
                            </Button>
                            <Button size="sm" onClick={handleSaveClass} disabled={isSaving} className="h-6 px-2 text-xs">
                                {isSaving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
                            </Button>
                        </>
                    )}
                    <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded">
                        <X className="h-3.5 w-3.5 text-slate-400" />
                    </button>
                </div>
            </div>

            {/* Color Picker */}
            {isEditMode && showColorPicker && (
                <div className="px-3 py-2 border-b border-slate-100 bg-slate-50">
                    <div className="flex flex-wrap gap-1.5">
                        {COLOR_OPTIONS.map((color) => (
                            <button
                                key={color}
                                onClick={() => {
                                    setEditingColor(color)
                                    setShowColorPicker(false)
                                }}
                                className={`w-5 h-5 rounded-full border-2 transition-transform hover:scale-110 ${editingColor === color ? 'border-slate-800 scale-110' : 'border-transparent'}`}
                                style={{ backgroundColor: color }}
                            />
                        ))}
                    </div>
                </div>
            )}

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-3 space-y-4">
                {loading ? (
                    <div className="flex items-center justify-center py-6">
                        <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
                    </div>
                ) : (
                    <>
                        {/* Properties */}
                        <section>
                            <h4 className="text-[10px] font-medium text-slate-400 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                                {t('components.detailPanel.properties')}
                                {isEditMode && !isAddingProp && (
                                    <button onClick={() => setIsAddingProp(true)} className="ml-auto text-blue-500 hover:text-blue-600">
                                        <Plus className="h-3 w-3" />
                                    </button>
                                )}
                            </h4>

                            {isEditMode && isAddingProp && (
                                <div className="flex flex-col gap-2 mb-2 bg-blue-50 p-2 rounded border border-blue-100">
                                    <div className="flex gap-1.5">
                                        <Input
                                            placeholder="属性名, 如: status"
                                            value={newProp}
                                            onChange={(e) => setNewProp(e.target.value)}
                                            className="h-7 text-xs bg-white flex-1"
                                            autoFocus
                                            onKeyDown={(e) => e.key === 'Enter' && handleConfirmAddProperty()}
                                        />
                                        <Select value={newPropType} onValueChange={setNewPropType}>
                                            <SelectTrigger className="h-7 text-xs bg-white w-[90px]">
                                                <SelectValue placeholder="类型" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {DATA_TYPES.map(type => (
                                                    <SelectItem key={type} value={type} className="text-xs">
                                                        {type}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="flex gap-1.5 justify-end">
                                        <Button size="sm" variant="ghost" className="h-6 px-2 text-xs" onClick={() => setIsAddingProp(false)}>取消</Button>
                                        <Button size="sm" className="h-6 px-3 text-xs" onClick={handleConfirmAddProperty}>确定</Button>
                                    </div>
                                </div>
                            )}

                            {(isEditMode ? editingProperties : (node.dataProperties || [])).length > 0 ? (
                                <div className="space-y-1">
                                    {(isEditMode ? editingProperties : (node.dataProperties || [])).map((prop, i) => (
                                        <div
                                            key={i}
                                            className="group flex items-center justify-between px-2 py-1 bg-slate-50 rounded text-xs font-mono text-slate-600 border border-slate-100"
                                        >
                                            <div className="flex justify-between w-full items-center min-w-0">
                                                <span className="truncate font-medium">{prop.split(':')[0]}</span>
                                                {prop.includes(':') && (
                                                    <span className="text-[9px] text-slate-400 ml-2 px-1 bg-slate-100 rounded flex-shrink-0">
                                                        {prop.split(':')[1]}
                                                    </span>
                                                )}
                                            </div>
                                            {isEditMode && (
                                                <button onClick={() => handleRemoveProperty(i)} className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600">
                                                    <Trash2 className="h-2.5 w-2.5" />
                                                </button>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-[10px] text-slate-300 italic">暂无属性</p>
                            )}
                        </section>

                        {/* Relationships */}
                        <section>
                            <h4 className="text-[10px] font-medium text-slate-400 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                                {t('components.ontology.relationships')}
                            </h4>
                            {relationships.length > 0 ? (
                                <div className="space-y-1">
                                    {relationships.map((rel, i) => (
                                        <div
                                            key={i}
                                            className="flex items-center gap-1 px-2 py-1 bg-slate-50 rounded text-[11px] border border-slate-100"
                                        >
                                            <span className={`truncate ${rel.direction === 'outgoing' ? 'text-blue-600 font-medium' : 'text-slate-500'}`}>
                                                {rel.source}
                                            </span>
                                            <ArrowRight className="h-2.5 w-2.5 flex-shrink-0 text-slate-300" />
                                            <span className={`px-1 py-0.5 rounded text-[10px] ${rel.direction === 'outgoing' ? 'bg-green-100 text-green-600' : 'bg-amber-100 text-amber-600'}`}>
                                                {rel.type}
                                            </span>
                                            <ArrowRight className="h-2.5 w-2.5 flex-shrink-0 text-slate-300" />
                                            <span className={`truncate ${rel.direction === 'incoming' ? 'text-blue-600 font-medium' : 'text-slate-500'}`}>
                                                {rel.target}
                                            </span>
                                            {isEditMode && (
                                                <button onClick={() => handleRemoveRelationship(rel)} className="ml-auto text-red-400 hover:text-red-600">
                                                    <Trash2 className="h-2.5 w-2.5" />
                                                </button>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-[10px] text-slate-300 italic">暂无关系</p>
                            )}
                        </section>

                        {/* Actions */}
                        <section>
                            <h4 className="text-[10px] font-medium text-slate-400 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-purple-500" />
                                {t('components.detailPanel.actions')}
                            </h4>
                            {actions.length > 0 ? (
                                <div className="space-y-1">
                                    {actions.map((action) => (
                                        <div
                                            key={action.id}
                                            className="flex items-center justify-between px-2 py-1 bg-slate-50 rounded text-xs border border-slate-100"
                                        >
                                            <div className="flex items-center gap-1.5">
                                                <Zap className="h-3 w-3 text-purple-500" />
                                                <span className="font-medium text-slate-600">{action.name}</span>
                                            </div>
                                            <span className={`px-1.5 py-0.5 rounded text-[10px] ${action.is_active ? 'bg-green-100 text-green-600' : 'bg-slate-100 text-slate-400'}`}>
                                                {action.is_active ? '启用' : '禁用'}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-[10px] text-slate-300 italic">暂无动作</p>
                            )}
                        </section>
                    </>
                )}
            </div>

            {isEditMode && node && (
                <div className="p-3 border-t border-slate-100">
                    {isConfirmDeleting ? (
                        <div className="bg-red-50 p-2 rounded border border-red-100 space-y-2">
                            <p className="text-[10px] text-red-600 text-center">
                                确定删除 <span className="font-medium">"{node.name}"</span>？
                            </p>
                            <div className="flex gap-1.5">
                                <Button
                                    variant="destructive"
                                    size="sm"
                                    className="flex-1 h-6 text-xs"
                                    onClick={handleDeleteNode}
                                    disabled={isDeleting}
                                >
                                    {isDeleting && <Loader2 className="h-3 w-3 animate-spin mr-1" />}
                                    确认
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="flex-1 h-6 text-xs"
                                    onClick={() => setIsConfirmDeleting(false)}
                                >
                                    取消
                                </Button>
                            </div>
                        </div>
                    ) : (
                        <Button
                            variant="outline"
                            size="sm"
                            className="w-full h-7 text-xs text-red-500 border-red-200 hover:bg-red-50"
                            onClick={() => setIsConfirmDeleting(true)}
                        >
                            <Trash2 className="h-3 w-3 mr-1" />
                            删除该类
                        </Button>
                    )}
                </div>
            )}
        </div>
    )
}
