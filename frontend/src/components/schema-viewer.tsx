'use client'

import { useEffect, useRef, useState } from 'react'
import cytoscape, { Core } from 'cytoscape'
import { graphApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { Crosshair } from 'lucide-react'
import { Button } from '@/components/ui/button'

// Professional color palette (muted, harmonious)
const SCHEMA_COLORS = [
    '#6366f1', '#8b5cf6', '#a855f7', '#d946ef', '#ec4899',
    '#f43f5e', '#f97316', '#eab308', '#84cc16', '#22c55e',
    '#14b8a6', '#06b6d4', '#0ea5e9', '#3b82f6', '#6366f1',
]

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

interface SchemaData {
    nodes: SchemaNode[]
    relationships: SchemaRelationship[]
}

interface SchemaViewerProps {
    onNodeSelect?: (node: SchemaNode | null) => void
    onEdgeSelect?: (edge: { source: string; target: string; relationship_type: string } | null) => void
    isEditMode?: boolean
    activeStep?: 'IDLE' | 'SOURCE' | 'TARGET' | 'TYPE'
    sourceNode?: string | null
    onSchemaChange?: () => void
}

export function SchemaViewer({
    onNodeSelect,
    onEdgeSelect,
    isEditMode,
    activeStep = 'IDLE',
    sourceNode,
    onSchemaChange
}: SchemaViewerProps) {
    const containerRef = useRef<HTMLDivElement>(null)
    const cyRef = useRef<Core | null>(null)
    const token = useAuthStore((state) => state.token)
    const [selectedNode, setSelectedNode] = useState<any>(null)
    const [legend, setLegend] = useState<{ name: string; color: string }[]>([])
    const [isMounted, setIsMounted] = useState(false)

    const onNodeSelectRef = useRef(onNodeSelect)
    const onEdgeSelectRef = useRef(onEdgeSelect)

    useEffect(() => {
        onNodeSelectRef.current = onNodeSelect
        onEdgeSelectRef.current = onEdgeSelect
    }, [onNodeSelect, onEdgeSelect])

    useEffect(() => {
        setIsMounted(true)
        return () => setIsMounted(false)
    }, [])

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
                    },
                },
                {
                    selector: '.selected-source',
                    style: {
                        'border-width': 3,
                        'border-color': '#22c55e',
                        'background-color': '#bbf7d0',
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
                        'text-background-padding': '2px',
                        'color': '#64748b',
                    }
                },
                {
                    selector: 'node:selected',
                    style: {
                        'border-color': '#3b82f6',
                        'border-width': 3,
                    }
                }
            ],
            layout: { name: 'preset' },
            minZoom: 0.3,
            maxZoom: 3,
        })

        cyRef.current.on('tap', 'node', (evt) => {
            const node = evt.target
            const nodeData = {
                name: node.id(),
                label: node.data('aliases'), // Use the stored aliases array
                dataProperties: node.data('dataProperties'),
                color: node.data('color'),
            }
            setSelectedNode(nodeData)
            onNodeSelectRef.current?.(nodeData)
        })

        cyRef.current.on('tap', 'edge', (evt) => {
            const edge = evt.target
            const edgeData = {
                source: edge.source().id(),
                target: edge.target().id(),
                relationship_type: edge.data('label'),
            }
            onEdgeSelectRef.current?.(edgeData)
        })

        cyRef.current.on('tap', (evt) => {
            if (evt.target === cyRef.current) {
                setSelectedNode(null)
                onNodeSelectRef.current?.(null)
                onEdgeSelectRef.current?.(null)
            }
        })

        return () => {
            cyRef.current?.destroy()
            cyRef.current = null
        }
    }, [isMounted])

    useEffect(() => {
        if (token && cyRef.current && isMounted) {
            loadSchema()
        }
    }, [token, isMounted, isEditMode, activeStep, sourceNode])

    const loadSchema = async () => {
        if (!cyRef.current || !isMounted) return

        try {
            const res = await graphApi.getSchema(token!)
            const data: SchemaData = res.data

            const colorMap: Record<string, string> = {}
            data.nodes.forEach((node, index) => {
                colorMap[node.name] = node.color || SCHEMA_COLORS[index % SCHEMA_COLORS.length]
            })

            setLegend(data.nodes.map((node, index) => ({
                name: node.name,
                color: node.color || SCHEMA_COLORS[index % SCHEMA_COLORS.length],
            })))

            const elements: any[] = []

            data.nodes.forEach((node) => {
                const color = colorMap[node.name]
                elements.push({
                    data: {
                        id: node.name,
                        label: node.name,
                        color: color,
                        borderColor: color,
                        aliases: node.label || [], // Store original label array
                        dataProperties: node.dataProperties || [],
                    }
                })
            })

            data.relationships.forEach((rel, index) => {
                elements.push({
                    data: {
                        id: `edge-${index}`,
                        source: rel.source,
                        target: rel.target,
                        label: rel.type,
                    }
                })
            })

            if (!cyRef.current || !isMounted) return

            cyRef.current.json({ elements })
            if (activeStep === 'TARGET' && sourceNode) {
                cyRef.current.getElementById(sourceNode).addClass('selected-source')
            }
            cyRef.current.layout({
                name: 'cose',
                animate: false,
            }).run()

        } catch (err) {
            console.error('Failed to load schema:', err)
            if (cyRef.current && isMounted) {
                cyRef.current.json({
                    elements: [{
                        data: {
                            id: 'error',
                            label: 'Schema 加载失败',
                            color: '#ef4444',
                            borderColor: '#dc2626',
                        }
                    }],
                })
            }
        }
    }

    const handleCenterGraph = () => {
        cyRef.current?.fit(undefined, 40)
    }

    return (
        <div className="relative w-full h-full">
            {/* Title Badge */}
            <div className="absolute top-3 left-3 z-10">
                <div className="bg-white/90 backdrop-blur-sm px-2.5 py-1 rounded-md shadow-sm text-xs font-medium text-slate-600 border border-slate-200">
                    Ontology (Schema)
                </div>
            </div>

            {/* Center Graph Button */}
            <div className="absolute top-3 right-3 z-10">
                <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCenterGraph}
                    className="h-7 w-7 p-0 bg-white/90 backdrop-blur-sm border-slate-200 hover:bg-white"
                    title="居中显示图谱"
                >
                    <Crosshair className="h-3.5 w-3.5 text-slate-500" />
                </Button>
            </div>

            {/* Graph Container */}
            <div
                ref={containerRef}
                className="w-full h-full rounded-lg border border-slate-200"
                style={{
                    background: '#f8fafc',
                }}
            />

            {/* Legend */}
            {legend.length > 0 && (
                <div className="absolute bottom-3 left-3 bg-white/95 backdrop-blur-sm text-slate-700 p-2.5 rounded-lg text-xs max-h-40 overflow-y-auto border border-slate-200 shadow-sm">
                    <div className="font-medium mb-1.5 text-slate-500 text-[10px] uppercase tracking-wide">Classes</div>
                    {legend.map((item) => (
                        <div
                            key={item.name}
                            className="flex items-center gap-1.5 py-0.5"
                        >
                            <div
                                className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                                style={{ backgroundColor: item.color }}
                            />
                            <span className="truncate">{item.name}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
