// frontend/src/components/instance-graph-viewer.tsx
'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import cytoscape, { Core, ElementDefinition } from 'cytoscape'
import { graphApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { ZoomIn, ZoomOut, Maximize2, Link as LinkIcon, Info } from 'lucide-react'
import { SearchParams } from './instance-filter'

// Neo4j-style color palette for different node labels
const NEO4J_COLORS = [
    '#4C8EDA', // Blue
    '#DA7194', // Pink
    '#569480', // Teal
    '#D9C8AE', // Beige
    '#604A0E', // Brown
    '#C990C0', // Purple
    '#F79767', // Orange
    '#57C7E3', // Cyan
    '#F16667', // Red
    '#8DCC93', // Green
]

const labelColorMap = new Map<string, string>()

function getColorForLabel(label: string): string {
    if (!labelColorMap.has(label)) {
        const colorIndex = labelColorMap.size % NEO4J_COLORS.length
        labelColorMap.set(label, NEO4J_COLORS[colorIndex])
    }
    return labelColorMap.get(label)!
}

interface InstanceNode {
    id: string
    name: string
    label: string
    nodeLabel: string
    labels?: string[]
    properties?: Record<string, any>
    color?: string
}

interface InstanceGraphViewerProps {
    searchParams: SearchParams | null
    onNodeSelect?: (node: InstanceNode | null) => void
    refreshTrigger?: number
}

export function InstanceGraphViewer({ searchParams, onNodeSelect, refreshTrigger }: InstanceGraphViewerProps) {
    const token = useAuthStore((state) => state.token)
    const containerRef = useRef<HTMLDivElement>(null)
    const cyRef = useRef<Core | null>(null)
    const [isMounted, setIsMounted] = useState(true)
    const [loading, setLoading] = useState(false)
    const [noData, setNoData] = useState(true)

    useEffect(() => {
        setIsMounted(true)
        return () => setIsMounted(false)
    }, [])

    useEffect(() => {
        if (!containerRef.current) return

        cyRef.current = cytoscape({
            container: containerRef.current,
            style: [
                {
                    selector: 'node',
                    style: {
                        'label': 'data(label)',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'background-color': 'data(color)',
                        'color': '#fff',
                        'width': 50,
                        'height': 50,
                        'font-size': 10,
                        'font-weight': 600,
                        'text-wrap': 'ellipsis',
                        'text-max-width': '60px',
                        'border-width': 2,
                        'border-color': 'data(borderColor)',
                        'text-outline-color': 'data(color)',
                        'text-outline-width': 1,
                    },
                },
                {
                    selector: 'node:selected',
                    style: {
                        'border-width': 3,
                        'border-color': '#A100FF',
                        'width': 60,
                        'height': 60,
                    },
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 2,
                        'line-color': '#A5ABB6',
                        'target-arrow-color': '#A5ABB6',
                        'target-arrow-shape': 'triangle',
                        'arrow-scale': 1.2,
                        'curve-style': 'bezier',
                        'label': 'data(label)',
                        'font-size': 10,
                        'color': '#64748b',
                        'text-background-color': '#ffffff',
                        'text-background-opacity': 0.9,
                        'text-background-padding': '3px',
                        'text-rotation': 'autorotate',
                        'text-margin-y': -10,
                    },
                },
                {
                    selector: 'edge:selected',
                    style: {
                        'width': 3,
                        'line-color': '#A100FF',
                        'target-arrow-color': '#A100FF',
                    },
                },
            ],
            layout: {
                name: 'cose',
                animate: true,
                animationDuration: 500,
                nodeRepulsion: () => 8000,
                idealEdgeLength: () => 120,
                gravity: 0.25,
            },
            wheelSensitivity: 0.3,
            minZoom: 0.2,
            maxZoom: 3,
        })

        // 双击展开邻居
        cyRef.current.on('dblclick', 'node', async (evt) => {
            const node = evt.target
            const nodeName = node.data('id')
            await expandNode(nodeName)
        })

        // 单击选中节点
        cyRef.current.on('tap', 'node', (evt) => {
            const node = evt.target
            const nodeData = node.data()
            onNodeSelect?.({
                id: nodeData.id,
                name: nodeData.label,
                label: nodeData.label,
                nodeLabel: nodeData.nodeLabel,
                labels: nodeData.labels,
                properties: nodeData.properties,
                color: nodeData.color,
            })
        })

        // 单击空白处取消选中
        cyRef.current.on('tap', (evt) => {
            if (evt.target === cyRef.current) {
                onNodeSelect?.(null)
            }
        })

        return () => {
            cyRef.current?.destroy()
            cyRef.current = null
        }
    }, [])

    // 当搜索参数变化时加载数据
    useEffect(() => {
        if (searchParams && token && cyRef.current) {
            loadInstances()
        }
    }, [searchParams, token, refreshTrigger])

    const loadInstances = async () => {
        if (!cyRef.current || !isMounted || !searchParams) return

        setLoading(true)
        setNoData(false)

        try {
            // 构建过滤条件
            const filterObj: Record<string, any> = {}
            searchParams.filters.forEach(f => {
                if (f.key && f.value) {
                    filterObj[f.key] = f.value
                }
            })

            // 搜索实例
            const res = await graphApi.searchInstances(
                searchParams.className,
                searchParams.keyword,
                filterObj,
                50,
                token!
            )

            const instances = res.data || []

            if (instances.length === 0) {
                setNoData(true)
                cyRef.current.json({ elements: [] })
                return
            }

            const elements: ElementDefinition[] = []
            const addedNodes = new Set<string>()
            const nodeColor = getColorForLabel(searchParams.className)
            const borderColor = shadeColor(nodeColor, -20)

            // 添加搜索到的节点
            instances.forEach((instance: any) => {
                const nodeName = instance.name
                if (!addedNodes.has(nodeName)) {
                    elements.push({
                        data: {
                            id: nodeName,
                            label: nodeName,
                            nodeLabel: searchParams.className,
                            labels: instance.labels,
                            color: nodeColor,
                            borderColor: borderColor,
                            properties: instance.properties,
                        },
                    })
                    addedNodes.add(nodeName)
                }
            })

            // 加载这些节点的邻居关系
            for (const instance of instances.slice(0, 20)) {
                try {
                    const neighborsRes = await graphApi.getNeighbors(instance.name, 1, token!)
                    const neighbors = neighborsRes.data || []

                    neighbors.forEach((n: any) => {
                        const labelName = n.labels?.[0] || 'Unknown'
                        const nColor = getColorForLabel(labelName)
                        const nBorderColor = shadeColor(nColor, -20)

                        if (!addedNodes.has(n.name)) {
                            elements.push({
                                data: {
                                    id: n.name,
                                    label: n.name,
                                    nodeLabel: labelName,
                                    labels: n.labels,
                                    color: nColor,
                                    borderColor: nBorderColor,
                                    properties: n.properties,
                                },
                            })
                            addedNodes.add(n.name)
                        }

                        // 添加边
                        n.relationships?.forEach((rel: any, i: number) => {
                            // Use consistent edge ID format (same as expandNode)
                            const edgeId = rel.id
                                ? `rel-${rel.id}`
                                : `${rel.source}-${rel.target}-${rel.type}`

                            if (!addedNodes.has(rel.source) || !addedNodes.has(rel.target)) return

                            elements.push({
                                data: {
                                    id: edgeId,
                                    source: rel.source,
                                    target: rel.target,
                                    label: rel.type,
                                },
                            })
                        })
                    })
                } catch (err) {
                    console.error('Failed to load neighbors:', err)
                }
            }

            if (!cyRef.current || !isMounted) return

            cyRef.current.json({ elements })
            cyRef.current.layout({
                name: 'cose',
                animate: true,
                animationDuration: 500,
                nodeRepulsion: () => 8000,
                idealEdgeLength: () => 120,
                gravity: 0.25,
            }).run()

        } catch (err) {
            console.error('Failed to load instances:', err)
            setNoData(true)
        } finally {
            setLoading(false)
        }
    }

    const expandNode = async (nodeName: string) => {
        try {
            const res = await graphApi.getNeighbors(nodeName, 1, token!)
            const neighbors = res.data

            const newElements: ElementDefinition[] = []
            const addedNodeIds = new Set<string>()
            const addedEdgeIds = new Set<string>()

            neighbors.forEach((n: any) => {
                const labelName = n.labels?.[0] || 'Unknown'
                const nodeColor = getColorForLabel(labelName)
                const borderColor = shadeColor(nodeColor, -20)

                // Add node if not exists (check both cytoscape and current batch)
                if (!cyRef.current?.getElementById(n.name).length && !addedNodeIds.has(n.name)) {
                    addedNodeIds.add(n.name)
                    newElements.push({
                        data: {
                            id: n.name,
                            label: n.name,
                            nodeLabel: labelName,
                            labels: n.labels,
                            color: nodeColor,
                            borderColor: borderColor,
                            properties: n.properties,
                        },
                    })
                }

                // Add edges
                n.relationships?.forEach((rel: any, i: number) => {
                    // Use relationship ID if available, otherwise fallback to composite key
                    const edgeId = rel.id
                        ? `rel-${rel.id}`
                        : `${rel.source}-${rel.target}-${rel.type}`

                    // Check both cytoscape and current batch to avoid duplicates
                    if (!cyRef.current?.getElementById(edgeId).length && !addedEdgeIds.has(edgeId)) {
                        // Ensure both nodes exist in the graph or current batch before adding the edge
                        const sourceExists = cyRef.current?.getElementById(rel.source).length || addedNodeIds.has(rel.source)
                        const targetExists = cyRef.current?.getElementById(rel.target).length || addedNodeIds.has(rel.target)

                        if (sourceExists && targetExists) {
                            addedEdgeIds.add(edgeId)
                            newElements.push({
                                data: {
                                    id: edgeId,
                                    source: rel.source,
                                    target: rel.target,
                                    label: rel.type,
                                },
                            })
                        }
                    }
                })
            })

            if (newElements.length > 0) {
                cyRef.current?.add(newElements)
                cyRef.current?.layout({
                    name: 'cose',
                    animate: true,
                    animationDuration: 500,
                    nodeRepulsion: () => 8000,
                    idealEdgeLength: () => 120,
                    gravity: 0.25,
                }).run()
            }
        } catch (err) {
            console.error('Failed to expand node:', err)
        }
    }

    const handleZoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)
    const handleZoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() * 0.8)
    const handleFit = () => cyRef.current?.fit()

    return (
        <div className="relative h-full">
            {/* 控制按钮 */}
            <div className="absolute top-4 left-4 z-10 flex flex-col gap-2">
                <Button size="icon" variant="secondary" onClick={handleZoomIn} className="bg-white/90 hover:bg-white shadow-md">
                    <ZoomIn className="h-4 w-4" />
                </Button>
                <Button size="icon" variant="secondary" onClick={handleZoomOut} className="bg-white/90 hover:bg-white shadow-md">
                    <ZoomOut className="h-4 w-4" />
                </Button>
                <Button size="icon" variant="secondary" onClick={handleFit} className="bg-white/90 hover:bg-white shadow-md">
                    <Maximize2 className="h-4 w-4" />
                </Button>
            </div>

            {/* 标题 */}
            <div className="absolute top-4 right-4 z-10 bg-white border border-slate-200 px-3 py-1.5 rounded-lg shadow-sm flex items-center gap-2 text-xs font-bold text-slate-700 uppercase tracking-widest">
                <LinkIcon className="h-3 w-3 text-primary" />
                实例图谱
            </div>

            {/* 图例 */}
            <div className="absolute bottom-4 left-4 z-10 bg-white/95 p-3 rounded-lg shadow-sm border border-slate-200">
                <h4 className="text-[10px] font-bold uppercase tracking-widest mb-2 text-slate-400">节点类型</h4>
                <div className="flex flex-wrap gap-2">
                    {Array.from(labelColorMap.entries()).map(([label, color]) => (
                        <div key={label} className="flex items-center gap-1">
                            <div
                                className="w-2.5 h-2.5 rounded-full"
                                style={{ backgroundColor: color }}
                            />
                            <span className="text-[10px] font-medium text-slate-600">{label}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* 提示信息 */}
            {noData && !loading && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div className="bg-white/90 px-6 py-4 rounded-lg shadow-lg text-center">
                        <p className="text-gray-500 text-sm">
                            {searchParams ? '未找到匹配的实例' : '请选择筛选条件并点击查询'}
                        </p>
                    </div>
                </div>
            )}

            {/* 加载中 */}
            {loading && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/10">
                    <div className="bg-white px-6 py-4 rounded-lg shadow-lg flex items-center gap-3">
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500" />
                        <span className="text-gray-600">加载中...</span>
                    </div>
                </div>
            )}

            <div
                ref={containerRef}
                className="w-full h-full"
                style={{ background: '#ffffff' }}
            />
        </div>
    )
}

// Helper function to shade colors
function shadeColor(color: string, percent: number): string {
    const num = parseInt(color.replace('#', ''), 16)
    const amt = Math.round(2.55 * percent)
    const R = (num >> 16) + amt
    const G = (num >> 8 & 0x00FF) + amt
    const B = (num & 0x0000FF) + amt
    return '#' + (
        0x1000000 +
        (R < 255 ? (R < 1 ? 0 : R) : 255) * 0x10000 +
        (G < 255 ? (G < 1 ? 0 : G) : 255) * 0x100 +
        (B < 255 ? (B < 1 ? 0 : B) : 255)
    ).toString(16).slice(1)
}
