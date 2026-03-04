// frontend/src/app/[locale]/admin/roles/components/BusinessRolePermissionEditor.tsx
'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { RoleDetail, rolesApi, graphApi, actionsApi, ActionInfo } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { toast } from 'sonner'
import {
    ArrowLeft,
    Check,
    X,
    Loader2,
    Zap,
    Eye,
    EyeOff,
    Crosshair,
    RefreshCw,
} from 'lucide-react'
import Link from 'next/link'
import { useLocale } from 'next-intl'
import { useAuthStore } from '@/lib/auth'
import cytoscape, { Core } from 'cytoscape'

interface BusinessRolePermissionEditorProps {
    role: RoleDetail
    onUpdated: () => void
}

interface SchemaNode {
    name: string
    label?: string[]
    dataProperties?: string[]
    color?: string
}

interface SchemaRelationship {
    source: string
    type: string
    target: string
}

const SCHEMA_COLORS = [
    '#6366f1', '#8b5cf6', '#a855f7', '#d946ef', '#ec4899',
    '#f43f5e', '#f97316', '#eab308', '#84cc16', '#22c55e',
    '#14b8a6', '#06b6d4', '#0ea5e9', '#3b82f6', '#6366f1',
]

export function BusinessRolePermissionEditor({ role, onUpdated }: BusinessRolePermissionEditorProps) {
    const locale = useLocale()
    const token = useAuthStore((state) => state.token)

    // Graph refs
    const containerRef = useRef<HTMLDivElement>(null)
    const cyRef = useRef<Core | null>(null)
    const [isMounted, setIsMounted] = useState(false)

    // Data
    const [schemaNodes, setSchemaNodes] = useState<SchemaNode[]>([])
    const [allActions, setAllActions] = useState<ActionInfo[]>([])
    const [loadingData, setLoadingData] = useState(true)

    // UI state
    const [selectedNode, setSelectedNode] = useState<SchemaNode | null>(null)
    const [togglingEntity, setTogglingEntity] = useState<string | null>(null)
    const [togglingAction, setTogglingAction] = useState<string | null>(null)

    const entityPermissions = role.entity_permissions || []
    const actionPermissions = role.action_permissions || []

    // Mount tracking
    useEffect(() => {
        setIsMounted(true)
        return () => setIsMounted(false)
    }, [])

    // Initialize cytoscape
    useEffect(() => {
        if (!containerRef.current || !isMounted) return

        cyRef.current = cytoscape({
            container: containerRef.current,
            style: [
                {
                    selector: 'node',
                    style: {
                        'label': 'data(label)',
                        'background-color': 'data(color)',
                        'color': '#1e293b',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'font-size': 10,
                        'font-weight': 500,
                        'width': 56,
                        'height': 56,
                        'text-wrap': 'ellipsis',
                        'text-max-width': '50px',
                        'border-width': 2,
                        'border-color': 'data(borderColor)',
                        'opacity': 'data(nodeOpacity)' as any,
                    },
                },
                {
                    selector: '.granted',
                    style: {
                        'border-color': '#22c55e',
                        'border-width': 3,
                    }
                },
                {
                    selector: '.not-granted',
                    style: {
                        'opacity': 0.35,
                        'border-style': 'dashed',
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'label': 'data(label)',
                        'curve-style': 'bezier',
                        'target-arrow-shape': 'triangle',
                        'target-arrow-color': '#94a3b8',
                        'line-color': '#cbd5e1',
                        'width': 1.5,
                        'font-size': 9,
                        'text-background-color': '#f8fafc',
                        'text-background-opacity': 1,
                        'text-background-padding': '2px' as any,
                        'color': '#64748b',
                    }
                },
                {
                    selector: 'node:selected',
                    style: {
                        'border-color': '#3b82f6',
                        'border-width': 4,
                        'opacity': 1,
                    }
                }
            ],
            layout: { name: 'preset' },
            minZoom: 0.3,
            maxZoom: 3,
        })

        cyRef.current.on('tap', 'node', (evt) => {
            const node = evt.target
            const nodeData: SchemaNode = {
                name: node.id(),
                label: node.data('aliases'),
                dataProperties: node.data('dataProperties'),
                color: node.data('color'),
            }
            setSelectedNode(nodeData)
        })

        cyRef.current.on('tap', (evt) => {
            if (evt.target === cyRef.current) {
                setSelectedNode(null)
            }
        })

        return () => {
            cyRef.current?.destroy()
            cyRef.current = null
        }
    }, [isMounted])

    // Load schema and actions
    useEffect(() => {
        if (token && isMounted) {
            loadData()
        }
    }, [token, isMounted])

    // Update node styles when permissions change
    const updateNodeStyles = useCallback(() => {
        if (!cyRef.current) return
        cyRef.current.nodes().forEach((node) => {
            const className = node.id()
            const granted = entityPermissions.includes(className)
            node.removeClass('granted not-granted')
            node.addClass(granted ? 'granted' : 'not-granted')
        })
    }, [entityPermissions])

    useEffect(() => {
        updateNodeStyles()
    }, [entityPermissions, updateNodeStyles])

    const loadData = async () => {
        setLoadingData(true)
        try {
            const [schemaRes, actionsRes] = await Promise.all([
                token ? graphApi.getSchema() : Promise.resolve({ data: { nodes: [], relationships: [] } }),
                actionsApi.list(),
            ])

            const nodes: SchemaNode[] = schemaRes.data.nodes || []
            const relationships: SchemaRelationship[] = schemaRes.data.relationships || []
            setSchemaNodes(nodes)
            setAllActions(actionsRes.data.actions || [])

            // Render graph
            if (cyRef.current && isMounted) {
                const colorMap: Record<string, string> = {}
                nodes.forEach((node, index) => {
                    colorMap[node.name] = node.color || SCHEMA_COLORS[index % SCHEMA_COLORS.length]
                })

                const elements: any[] = []

                nodes.forEach((node) => {
                    const color = colorMap[node.name]
                    const granted = entityPermissions.includes(node.name)
                    elements.push({
                        data: {
                            id: node.name,
                            label: node.name,
                            color: color,
                            borderColor: granted ? '#22c55e' : color,
                            aliases: node.label || [],
                            dataProperties: node.dataProperties || [],
                            nodeOpacity: granted ? 1 : 0.35,
                        },
                        classes: granted ? 'granted' : 'not-granted',
                    })
                })

                relationships.forEach((rel, index) => {
                    elements.push({
                        data: {
                            id: `edge-${index}`,
                            source: rel.source,
                            target: rel.target,
                            label: rel.type,
                        }
                    })
                })

                cyRef.current.json({ elements })
                cyRef.current.layout({
                    name: 'cose',
                    animate: false,
                }).run()
            }
        } catch (err) {
            console.error('Failed to load data:', err)
            toast.error('Failed to load ontology data')
        } finally {
            setLoadingData(false)
        }
    }

    // Check permissions
    const isEntityGranted = (className: string) => entityPermissions.includes(className)
    const isActionGranted = (entityType: string, actionName: string) =>
        actionPermissions.some(p => p.entity_type === entityType && p.action_name === actionName)

    // Toggle entity
    const handleToggleEntity = async (className: string) => {
        setTogglingEntity(className)
        try {
            if (isEntityGranted(className)) {
                await rolesApi.removeEntityPermission(role.id, className)
                toast.success(`Revoked visibility: ${className}`)
            } else {
                await rolesApi.addEntityPermission(role.id, className)
                toast.success(`Granted visibility: ${className}`)
            }
            onUpdated()
        } catch (err) {
            console.error('Failed to toggle entity permission:', err)
            toast.error('Failed to update permission')
        } finally {
            setTogglingEntity(null)
        }
    }

    // Toggle action
    const handleToggleAction = async (entityType: string, actionName: string) => {
        const key = `${entityType}:${actionName}`
        setTogglingAction(key)
        try {
            if (isActionGranted(entityType, actionName)) {
                await rolesApi.removeActionPermission(role.id, entityType, actionName)
                toast.success(`Revoked action: ${actionName}`)
            } else {
                await rolesApi.addActionPermission(role.id, entityType, actionName)
                toast.success(`Granted action: ${actionName}`)
            }
            onUpdated()
        } catch (err) {
            console.error('Failed to toggle action permission:', err)
            toast.error('Failed to update permission')
        } finally {
            setTogglingAction(null)
        }
    }

    const handleCenterGraph = () => {
        cyRef.current?.fit(undefined, 40)
    }

    // Actions for currently selected node
    const selectedNodeActions = selectedNode
        ? allActions.filter(a => a.entity_type === selectedNode.name)
        : []

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center gap-4">
                <Link href={`/${locale}/admin/roles`}>
                    <Button variant="ghost" size="sm" className="flex items-center gap-1.5">
                        <ArrowLeft className="w-4 h-4" />
                        Back
                    </Button>
                </Link>
                <div className="flex-1">
                    <h1 className="text-2xl font-bold flex items-center gap-2">
                        {role.name}
                        <span className="text-[10px] bg-blue-50 px-1.5 py-0.5 rounded text-blue-600 uppercase font-bold tracking-wider">
                            Business Role
                        </span>
                    </h1>
                    <p className="text-sm text-gray-500">{role.description || 'No description'}</p>
                </div>
                <div className="text-right text-sm text-gray-400">
                    <div><strong className="text-green-600">{entityPermissions.length}</strong> entities visible</div>
                    <div><strong className="text-purple-600">{actionPermissions.length}</strong> actions granted</div>
                </div>
            </div>

            {/* Main Layout: Graph + Side Panel */}
            <div className="flex gap-4" style={{ height: 'calc(100vh - 200px)', minHeight: 500 }}>
                {/* Graph Area */}
                <div className="flex-1 relative rounded-lg border border-slate-200 overflow-hidden">
                    {/* Title badge */}
                    <div className="absolute top-3 left-3 z-10">
                        <div className="bg-white/90 backdrop-blur-sm px-2.5 py-1 rounded-md shadow-sm text-xs font-medium text-slate-600 border border-slate-200">
                            Click a node to manage permissions
                        </div>
                    </div>

                    {/* Toolbar */}
                    <div className="absolute top-3 right-3 z-10 flex gap-1.5">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={handleCenterGraph}
                            className="h-7 w-7 p-0 bg-white/90 backdrop-blur-sm border-slate-200 hover:bg-white"
                            title="Center graph"
                        >
                            <Crosshair className="h-3.5 w-3.5 text-slate-500" />
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={loadData}
                            className="h-7 w-7 p-0 bg-white/90 backdrop-blur-sm border-slate-200 hover:bg-white"
                            title="Refresh"
                            disabled={loadingData}
                        >
                            <RefreshCw className={`h-3.5 w-3.5 text-slate-500 ${loadingData ? 'animate-spin' : ''}`} />
                        </Button>
                    </div>

                    {/* Cytoscape container */}
                    <div
                        ref={containerRef}
                        className="w-full h-full"
                        style={{ background: '#f8fafc' }}
                    />

                    {/* Legend */}
                    <div className="absolute bottom-3 left-3 bg-white/95 backdrop-blur-sm text-slate-700 p-2.5 rounded-lg text-xs max-h-40 overflow-y-auto border border-slate-200 shadow-sm">
                        <div className="font-medium mb-1.5 text-slate-500 text-[10px] uppercase tracking-wide">Legend</div>
                        <div className="flex items-center gap-1.5 py-0.5">
                            <div className="w-3 h-3 rounded-full border-2 border-green-500 bg-green-100 flex-shrink-0" />
                            <span>Visible (granted)</span>
                        </div>
                        <div className="flex items-center gap-1.5 py-0.5">
                            <div className="w-3 h-3 rounded-full border-2 border-dashed border-gray-300 bg-gray-100 flex-shrink-0 opacity-50" />
                            <span>Hidden (not granted)</span>
                        </div>
                    </div>

                    {loadingData && (
                        <div className="absolute inset-0 bg-white/60 flex items-center justify-center z-20">
                            <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                        </div>
                    )}
                </div>

                {/* Side Panel */}
                <div className="w-[340px] flex-shrink-0 border border-slate-200 rounded-lg bg-white overflow-y-auto">
                    {selectedNode ? (
                        <div className="p-4 space-y-5">
                            {/* Node Header */}
                            <div>
                                <div className="flex items-center gap-2 mb-1">
                                    <div
                                        className="w-4 h-4 rounded-full flex-shrink-0"
                                        style={{ backgroundColor: selectedNode.color || '#6366f1' }}
                                    />
                                    <h3 className="text-lg font-bold">{selectedNode.name}</h3>
                                </div>
                                {selectedNode.label && selectedNode.label.length > 0 && (
                                    <p className="text-xs text-gray-400 ml-6">{selectedNode.label.join(', ')}</p>
                                )}
                            </div>

                            {/* Entity Visibility Toggle */}
                            <div className="border rounded-lg p-3">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        {isEntityGranted(selectedNode.name) ? (
                                            <Eye className="w-4 h-4 text-green-600" />
                                        ) : (
                                            <EyeOff className="w-4 h-4 text-gray-400" />
                                        )}
                                        <span className="text-sm font-medium">Node Visibility</span>
                                    </div>
                                    <Button
                                        variant={isEntityGranted(selectedNode.name) ? 'default' : 'outline'}
                                        size="sm"
                                        className={isEntityGranted(selectedNode.name) ? 'bg-green-600 hover:bg-green-700' : ''}
                                        onClick={() => handleToggleEntity(selectedNode.name)}
                                        disabled={togglingEntity === selectedNode.name}
                                    >
                                        {togglingEntity === selectedNode.name ? '...' : isEntityGranted(selectedNode.name) ? (
                                            <span className="flex items-center gap-1"><Check className="w-3.5 h-3.5" /> Visible</span>
                                        ) : (
                                            <span className="flex items-center gap-1"><X className="w-3.5 h-3.5" /> Hidden</span>
                                        )}
                                    </Button>
                                </div>
                                <p className="text-[11px] text-gray-400 mt-1.5">
                                    {isEntityGranted(selectedNode.name)
                                        ? 'Users with this role can see instances of this entity type.'
                                        : 'Users with this role cannot see instances of this entity type.'}
                                </p>
                            </div>

                            {/* Properties */}
                            {selectedNode.dataProperties && selectedNode.dataProperties.length > 0 && (
                                <div>
                                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Properties</h4>
                                    <div className="flex flex-wrap gap-1.5">
                                        {selectedNode.dataProperties.map((prop) => (
                                            <span key={prop} className="text-[11px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                                                {prop}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Actions Section */}
                            <div>
                                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                                    <Zap className="w-3 h-3 text-purple-500" />
                                    Executable Actions
                                </h4>

                                {selectedNodeActions.length === 0 ? (
                                    <div className="text-xs text-gray-400 border border-dashed rounded-md p-3 text-center">
                                        No actions defined for this entity type
                                    </div>
                                ) : (
                                    <div className="space-y-1.5">
                                        {selectedNodeActions.map((action) => {
                                            const granted = isActionGranted(selectedNode.name, action.name)
                                            const key = `${selectedNode.name}:${action.name}`
                                            const isToggling = togglingAction === key
                                            return (
                                                <label
                                                    key={key}
                                                    className={`flex items-center gap-3 p-2.5 rounded-md border cursor-pointer transition-colors ${granted
                                                        ? 'border-purple-200 bg-purple-50/30'
                                                        : 'border-gray-100 hover:border-gray-200'
                                                        } ${isToggling ? 'opacity-50 pointer-events-none' : ''}`}
                                                >
                                                    <Checkbox
                                                        checked={granted}
                                                        onChange={() => handleToggleAction(selectedNode.name, action.name)}
                                                        disabled={isToggling || !isEntityGranted(selectedNode.name)}
                                                    />
                                                    <div className="flex-1 min-w-0">
                                                        <span className="text-sm font-medium block truncate">{action.name}</span>
                                                    </div>
                                                    {granted && <Check className="w-3 h-3 text-purple-500 flex-shrink-0" />}
                                                </label>
                                            )
                                        })}
                                        {!isEntityGranted(selectedNode.name) && selectedNodeActions.length > 0 && (
                                            <p className="text-[10px] text-amber-600 mt-1">
                                                ⚠ Grant visibility first to enable action permissions
                                            </p>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        /* Empty state */
                        <div className="h-full flex flex-col items-center justify-center text-gray-400 p-6">
                            <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mb-3">
                                <Crosshair className="w-5 h-5" />
                            </div>
                            <p className="text-sm font-medium text-gray-500">Select a node</p>
                            <p className="text-xs text-center mt-1">
                                Click on an ontology class in the graph to manage its visibility and action permissions.
                            </p>
                            <div className="mt-6 w-full">
                                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                                    Quick Overview
                                </h4>
                                <div className="space-y-1">
                                    {schemaNodes.map((cls) => {
                                        const granted = isEntityGranted(cls.name)
                                        return (
                                            <div
                                                key={cls.name}
                                                className={`flex items-center gap-2 px-2 py-1 rounded text-xs cursor-pointer hover:bg-gray-50 ${granted ? 'text-gray-700' : 'text-gray-400'
                                                    }`}
                                                onClick={() => {
                                                    setSelectedNode(cls)
                                                    // Also select in graph
                                                    if (cyRef.current) {
                                                        cyRef.current.nodes().unselect()
                                                        cyRef.current.getElementById(cls.name).select()
                                                    }
                                                }}
                                            >
                                                {granted ? (
                                                    <Eye className="w-3 h-3 text-green-500" />
                                                ) : (
                                                    <EyeOff className="w-3 h-3 text-gray-300" />
                                                )}
                                                <span className="truncate">{cls.name}</span>
                                            </div>
                                        )
                                    })}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
