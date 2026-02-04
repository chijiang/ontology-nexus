// frontend/src/components/instance-detail-panel.tsx
'use client'

import { useState, useEffect } from 'react'
import { graphApi, actionsApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { X, Save, Edit2, Check, XCircle, Play, Loader2 } from 'lucide-react'
import { toast } from 'sonner'

interface InstanceNode {
    id: string
    name: string
    label: string
    nodeLabel: string
    labels?: string[]
    properties?: Record<string, any>
}

interface InstanceDetailPanelProps {
    node: InstanceNode | null
    onClose: () => void
    onUpdate?: () => void
}

export function InstanceDetailPanel({ node, onClose, onUpdate }: InstanceDetailPanelProps) {
    const token = useAuthStore((state) => state.token)
    const [editing, setEditing] = useState(false)
    const [editedProperties, setEditedProperties] = useState<Record<string, any>>({})
    const [saving, setSaving] = useState(false)
    const [expandedProps, setExpandedProps] = useState<Record<string, any>>({})
    const [actions, setActions] = useState<any[]>([])
    const [executingAction, setExecutingAction] = useState<string | null>(null)

    useEffect(() => {
        if (node) {
            // 加载完整的属性
            loadNodeDetails()
            // 加载可用操作
            loadActions()
        }
    }, [node])

    const loadNodeDetails = async () => {
        if (!node || !token) return

        try {
            const res = await graphApi.getNode(node.id || node.name, token)
            const props = res.data || {}
            // 过滤内部属性
            const filteredProps: Record<string, any> = {}
            Object.entries(props).forEach(([key, value]) => {
                if (!key.startsWith('__') && key !== 'uri') {
                    filteredProps[key] = value
                }
            })
            setExpandedProps(filteredProps)
            setEditedProperties(filteredProps)
        } catch (err) {
            console.error('Failed to load node details:', err)
            // 使用已有的属性
            const props = node.properties || {}
            setExpandedProps(props)
            setEditedProperties(props)
        }
    }

    const handleStartEdit = () => {
        setEditing(true)
        setEditedProperties({ ...expandedProps })
    }

    const handleCancelEdit = () => {
        setEditing(false)
        setEditedProperties({ ...expandedProps })
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
            // 只发送修改过的属性
            const updates: Record<string, any> = {}
            Object.entries(editedProperties).forEach(([key, value]) => {
                if (expandedProps[key] !== value) {
                    updates[key] = value
                }
            })

            if (Object.keys(updates).length === 0) {
                toast.info('没有属性被修改')
                setEditing(false)
                return
            }

            await graphApi.updateEntity(node.nodeLabel, node.name, updates, token)
            toast.success('属性更新成功')
            setExpandedProps({ ...editedProperties })
            setEditing(false)
            onUpdate?.()
        } catch (err: any) {
            console.error('Failed to update entity:', err)
            toast.error(err.response?.data?.detail || '更新失败')
        } finally {
            setSaving(false)
        }
    }

    const loadActions = async () => {
        if (!node || !token) return

        try {
            // 获取所有标签对应的操作
            const labels = node.labels || [node.nodeLabel]
            const allActions: any[] = []

            for (const label of labels) {
                const res = await actionsApi.listByEntityType(label)
                if (res.data?.actions) {
                    allActions.push(...res.data.actions)
                }
            }

            // 去重
            const uniqueActions = Array.from(new Map(allActions.map(a => [`${a.entity_type}.${a.action_name}`, a])).values())
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
            const res = await actionsApi.execute(
                action.entity_type,
                action.action_name,
                node.name,
                expandedProps
            )

            if (res.data?.success) {
                toast.success(res.data.message || '操作执行成功')
                // 刷新数据
                loadNodeDetails()
                onUpdate?.()
            } else {
                toast.warning(res.data?.message || res.data?.detail || '操作失败')
            }
        } catch (err: any) {
            // 只在非业务逻辑错误时记录详细日志
            const errorMessage = err.response?.data?.detail || err.message || '操作执行失败'
            toast.error(errorMessage)
        } finally {
            setExecutingAction(null)
        }
    }

    if (!node) return null

    const displayProps = editing ? editedProperties : expandedProps

    return (
        <div className="bg-white rounded-lg shadow-lg border h-full flex flex-col">
            {/* 头部 */}
            <div className="p-4 border-b flex items-center justify-between bg-gradient-to-r from-emerald-50 to-teal-50">
                <div className="flex items-center gap-2">
                    <div
                        className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold"
                        style={{ backgroundColor: node.properties?.color || '#4C8EDA' }}
                    >
                        {node.nodeLabel?.charAt(0) || 'E'}
                    </div>
                    <div>
                        <h3 className="font-semibold text-gray-800">{node.name}</h3>
                        <p className="text-xs text-gray-500">{node.nodeLabel}</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    {!editing ? (
                        <Button variant="ghost" size="sm" onClick={handleStartEdit}>
                            <Edit2 className="h-4 w-4" />
                        </Button>
                    ) : (
                        <>
                            <Button variant="ghost" size="sm" onClick={handleCancelEdit}>
                                <XCircle className="h-4 w-4 text-gray-500" />
                            </Button>
                            <Button
                                variant="default"
                                size="sm"
                                onClick={handleSave}
                                disabled={saving}
                            >
                                {saving ? (
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                                ) : (
                                    <Check className="h-4 w-4" />
                                )}
                            </Button>
                        </>
                    )}
                    <button
                        onClick={onClose}
                        className="p-1 hover:bg-gray-200 rounded transition-colors"
                    >
                        <X className="h-4 w-4 text-gray-500" />
                    </button>
                </div>
            </div>

            {/* 属性列表 */}
            <div className="flex-1 overflow-y-auto p-4">
                <h4 className="text-sm font-semibold text-gray-700 mb-3">实体属性</h4>

                {Object.keys(displayProps).length === 0 ? (
                    <p className="text-sm text-gray-400 italic">暂无属性</p>
                ) : (
                    <div className="space-y-3">
                        {Object.entries(displayProps).map(([key, value]) => (
                            <div key={key} className="space-y-1">
                                <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                                    {key}
                                </label>
                                {editing ? (
                                    <Input
                                        value={String(value ?? '')}
                                        onChange={(e) => handlePropertyChange(key, e.target.value)}
                                        className="w-full text-sm"
                                    />
                                ) : (
                                    <div className="px-3 py-2 bg-gray-50 rounded-lg text-sm text-gray-700 border border-gray-100">
                                        {formatValue(value)}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}

                {/* 可用操作 */}
                {actions.length > 0 && (
                    <div className="mt-6 pt-6 border-t">
                        <h4 className="text-sm font-semibold text-gray-700 mb-3">可用操作</h4>
                        <div className="flex flex-wrap gap-2">
                            {actions.map((action) => {
                                const actionKey = `${action.entity_type}.${action.action_name}`
                                const isExecuting = executingAction === actionKey

                                return (
                                    <Button
                                        key={actionKey}
                                        variant="outline"
                                        size="sm"
                                        className="gap-2 border-emerald-200 hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-300"
                                        onClick={() => handleExecuteAction(action)}
                                        disabled={!!executingAction}
                                    >
                                        {isExecuting ? (
                                            <Loader2 className="h-4 w-4 animate-spin text-emerald-600" />
                                        ) : (
                                            <Play className="h-3 w-3 text-emerald-600 fill-emerald-600" />
                                        )}
                                        {action.action_name}
                                    </Button>
                                )
                            })}
                        </div>
                    </div>
                )}
            </div>

            {/* 编辑模式提示 */}
            {editing && (
                <div className="p-3 bg-yellow-50 border-t border-yellow-100">
                    <p className="text-xs text-yellow-700">
                        正在编辑模式 - 修改属性值后点击保存
                    </p>
                </div>
            )}
        </div>
    )
}

function formatValue(value: any): string {
    if (value === null || value === undefined) return '-'
    if (typeof value === 'boolean') return value ? '是' : '否'
    if (Array.isArray(value)) return value.join(', ')
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
}
