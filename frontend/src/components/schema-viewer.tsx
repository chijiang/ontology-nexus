'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import cytoscape, { Core } from 'cytoscape'
import { graphApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'

// Schema 节点颜色（蓝色系，与 Instance 区分）
const SCHEMA_COLORS = [
    '#4A90D9', '#5B9BD5', '#6BA3E0', '#7CADE5', '#8DB7EA',
    '#9EC1EF', '#AFCBF4', '#C0D5F9', '#3B82D9', '#2B72C9',
]

interface SchemaNode {
    name: string
    label?: string
    dataProperties?: string[]
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

export function SchemaViewer() {
    const containerRef = useRef<HTMLDivElement>(null)
    const cyRef = useRef<Core | null>(null)
    const token = useAuthStore((state) => state.token)
    const [selectedNode, setSelectedNode] = useState<any>(null)
    const [legend, setLegend] = useState<{ name: string; color: string }[]>([])
    const [isMounted, setIsMounted] = useState(false)

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
                        'color': '#fff',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'font-size': 11,
                        'font-weight': 600,
                        'width': 80,
                        'height': 80,
                        'text-wrap': 'ellipsis',
                        'text-max-width': '70px',
                        'border-width': 3,
                        'border-color': 'data(borderColor)',
                        'text-outline-color': 'data(color)',
                        'text-outline-width': 2,
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'label': 'data(label)',
                        'curve-style': 'bezier',
                        'target-arrow-shape': 'triangle',
                        'target-arrow-color': '#666',
                        'line-color': '#888',
                        'width': 2,
                        'font-size': 10,
                        'text-background-color': '#fff',
                        'text-background-opacity': 1,
                        'text-background-padding': '3px',
                        'color': '#444',
                    }
                },
                {
                    selector: 'node:selected',
                    style: {
                        'border-color': '#FFD700',
                        'border-width': 4,
                    }
                }
            ],
            layout: { name: 'preset' },
            minZoom: 0.3,
            maxZoom: 3,
        })

        cyRef.current.on('tap', 'node', (evt) => {
            const node = evt.target
            setSelectedNode({
                name: node.data('label'),
                dataProperties: node.data('dataProperties'),
            })
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

    useEffect(() => {
        if (token && cyRef.current && isMounted) {
            loadSchema()
        }
    }, [token, isMounted])

    const loadSchema = async () => {
        if (!cyRef.current || !isMounted) return

        try {
            const res = await graphApi.getSchema(token!)
            const data: SchemaData = res.data

            // 构建颜色映射
            const colorMap: Record<string, string> = {}
            data.nodes.forEach((node, index) => {
                colorMap[node.name] = SCHEMA_COLORS[index % SCHEMA_COLORS.length]
            })

            // 构建图例
            setLegend(data.nodes.map((node, index) => ({
                name: node.name,
                color: SCHEMA_COLORS[index % SCHEMA_COLORS.length],
            })))

            // 构建 Cytoscape 元素
            const elements: any[] = []

            data.nodes.forEach((node) => {
                const color = colorMap[node.name]
                elements.push({
                    data: {
                        id: node.name,
                        label: node.name,
                        color: color,
                        borderColor: color,
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
            cyRef.current.layout({
                name: 'cose',
                animate: true,
                animationDuration: 500,
                nodeRepulsion: () => 10000,
                idealEdgeLength: () => 150,
                gravity: 0.2,
            }).run()

        } catch (err) {
            console.error('Failed to load schema:', err)
            if (cyRef.current && isMounted) {
                cyRef.current.json({
                    elements: [{
                        data: {
                            id: 'error',
                            label: 'Schema 加载失败',
                            color: '#F16667',
                            borderColor: '#C44',
                        }
                    }],
                })
            }
        }
    }

    return (
        <div className="relative w-full h-full">
            {/* 标题 */}
            <div className="absolute top-2 left-2 z-10 bg-white/90 px-3 py-1 rounded-lg shadow text-sm font-semibold text-blue-700">
                📋 Ontology (Schema)
            </div>

            {/* 图谱容器 */}
            <div
                ref={containerRef}
                className="w-full h-full rounded-lg"
                style={{
                    background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
                }}
            />

            {/* 图例 */}
            {legend.length > 0 && (
                <div className="absolute bottom-4 left-4 bg-black/70 text-white p-3 rounded-lg text-xs max-h-48 overflow-y-auto">
                    <div className="font-semibold mb-2">Classes</div>
                    {legend.map((item) => (
                        <div key={item.name} className="flex items-center gap-2 py-0.5">
                            <div
                                className="w-3 h-3 rounded-full"
                                style={{ backgroundColor: item.color }}
                            />
                            <span>{item.name}</span>
                        </div>
                    ))}
                </div>
            )}

            {/* 节点详情 */}
            {selectedNode && (
                <div className="absolute top-4 right-4 bg-white p-4 rounded-lg shadow-lg max-w-xs">
                    <h3 className="font-semibold text-lg mb-2">{selectedNode.name}</h3>
                    {selectedNode.dataProperties && selectedNode.dataProperties.length > 0 && (
                        <div>
                            <div className="text-sm text-gray-500 mb-1">属性：</div>
                            <ul className="text-sm">
                                {selectedNode.dataProperties.map((prop: string, i: number) => (
                                    <li key={i} className="text-gray-700">• {prop}</li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
