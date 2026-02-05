// frontend/src/components/graph-preview.tsx
'use client'

import { useEffect, useRef, useCallback, useState } from 'react'
import cytoscape, { Core, NodeSingular } from 'cytoscape'
import { X, ZoomIn, ZoomOut, Maximize2, RotateCcw, Play, Pause } from 'lucide-react'

interface GraphNode {
  id: string
  label: string
  type?: string
  properties?: Record<string, any>
}

interface GraphEdge {
  source: string
  target: string
  label?: string
}

interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

interface SelectedNode {
  id: string
  label: string
  type: string
  properties: Record<string, string>
  connections: { direction: 'in' | 'out'; label: string; node: string }[]
}

// 根据类型获取节点颜色 - 使用单色
const getNodeColor = (type: string): string => {
  const colors: Record<string, string> = {
    'PurchaseOrder': '#6366f1',
    'GoodsReceipt': '#10b981',
    'Supplier': '#f59e0b',
    'PurchaseContract': '#8b5cf6',
    'SupplierInvoice': '#ec4899',
    'Payment': '#14b8a6',
    'Material': '#f97316',
    'Class': '#3b82f6',
    'default': '#64748b'
  }
  return colors[type] || colors.default
}

export function GraphPreview({ data }: { data: GraphData | null }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)
  const layoutRef = useRef<any>(null)
  const [selectedNode, setSelectedNode] = useState<SelectedNode | null>(null)
  const [isAnimating, setIsAnimating] = useState(true)

  const hasData = data && data.nodes && data.nodes.length > 0

  // 启动力学动画布局
  const startForceLayout = useCallback(() => {
    if (!cyRef.current) return

    // 停止之前的布局
    if (layoutRef.current) {
      layoutRef.current.stop()
    }

    // 使用 cose 布局模拟力学效果
    layoutRef.current = cyRef.current.layout({
      name: 'cose',
      animate: true,
      animationDuration: 500,
      animationEasing: 'ease-out',
      fit: true,
      padding: 50,
      nodeOverlap: 20,
      componentSpacing: 100,
      nodeRepulsion: () => 8000,
      idealEdgeLength: () => 120,
      gravity: 0.25,
      numIter: 1000,
      initialTemp: 200,
      coolingFactor: 0.95,
      minTemp: 1.0,
      randomize: false,
    })

    layoutRef.current.run()
  }, [])

  // 初始化图谱
  const initOrUpdateGraph = useCallback(() => {
    if (!containerRef.current || !hasData || !data) return

    // 销毁旧实例
    if (cyRef.current) {
      cyRef.current.destroy()
      cyRef.current = null
    }

    // 构建元素
    const elements = [
      ...data.nodes.map((n) => ({
        data: {
          id: n.id,
          label: n.label,
          type: n.type || 'default',
          color: getNodeColor(n.type || 'default'),
          properties: n.properties || {}
        }
      })),
      ...(data.edges || []).map((e, i) => ({
        data: { id: `e${i}`, source: e.source, target: e.target, label: e.label || '' },
      })),
    ]

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-margin-y': 8,
            'background-color': 'data(color)',
            'color': '#e2e8f0',
            'width': 45,
            'height': 45,
            'font-size': 11,
            'font-weight': 500,
            'text-wrap': 'ellipsis',
            'text-max-width': '100px',
            'border-width': 3,
            'border-color': '#1e293b',
            'transition-property': 'width, height, border-width, border-color',
            'transition-duration': 150,
          },
        },
        {
          selector: 'node:selected',
          style: {
            'border-color': '#fbbf24',
            'border-width': 4,
            'width': 55,
            'height': 55,
          },
        },
        {
          selector: 'node:active',
          style: {
            'overlay-opacity': 0.1,
          },
        },
        {
          selector: 'node:grabbed',
          style: {
            'border-color': '#94a3b8',
          },
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#475569',
            'target-arrow-color': '#475569',
            'target-arrow-shape': 'triangle',
            'arrow-scale': 1.2,
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': 9,
            'color': '#94a3b8',
            'text-rotation': 'autorotate',
            'text-margin-y': -10,
            'text-background-color': '#1e293b',
            'text-background-opacity': 0.8,
            'text-background-padding': '3px',
          },
        },
        {
          selector: 'edge:selected',
          style: {
            'line-color': '#fbbf24',
            'target-arrow-color': '#fbbf24',
            'width': 3,
          },
        },
      ],
      layout: { name: 'preset' }, // 先用 preset，然后手动启动动画
      minZoom: 0.3,
      maxZoom: 3,
      wheelSensitivity: 0.3,
    })

    // 节点拖拽
    cyRef.current.nodes().forEach(node => {
      node.grabify()
    })

    // 节点点击事件
    cyRef.current.on('tap', 'node', (e) => {
      const node = e.target as NodeSingular
      const nodeData = node.data()

      const connectedEdges = node.connectedEdges()
      const connections: SelectedNode['connections'] = []

      connectedEdges.forEach((edge) => {
        const edgeData = edge.data()
        if (edgeData.source === nodeData.id) {
          connections.push({
            direction: 'out',
            label: edgeData.label || '关联',
            node: edgeData.target
          })
        } else {
          connections.push({
            direction: 'in',
            label: edgeData.label || '关联',
            node: edgeData.source
          })
        }
      })

      setSelectedNode({
        id: nodeData.id,
        label: nodeData.label,
        type: nodeData.type,
        properties: { name: nodeData.label, type: nodeData.type, ...nodeData.properties },
        connections
      })
    })

    // 点击空白处取消选中
    cyRef.current.on('tap', (e) => {
      if (e.target === cyRef.current) {
        setSelectedNode(null)
      }
    })

    // 启动力学布局
    if (isAnimating) {
      startForceLayout()
    }

  }, [hasData, data, isAnimating, startForceLayout])

  // 当数据变化时更新图谱
  useEffect(() => {
    if (hasData) {
      const timer = setTimeout(() => {
        initOrUpdateGraph()
      }, 50)
      return () => clearTimeout(timer)
    } else {
      setSelectedNode(null)
    }
  }, [hasData, data, initOrUpdateGraph])

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      if (layoutRef.current) {
        layoutRef.current.stop()
      }
      if (cyRef.current) {
        cyRef.current.destroy()
        cyRef.current = null
      }
    }
  }, [])

  // 控制函数
  const handleZoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.3)
  const handleZoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() * 0.7)
  const handleFit = () => cyRef.current?.fit(undefined, 50)
  const handleReset = () => startForceLayout()
  const toggleAnimation = () => {
    if (isAnimating && layoutRef.current) {
      layoutRef.current.stop()
    } else {
      startForceLayout()
    }
    setIsAnimating(!isAnimating)
  }

  // 获取唯一类型列表
  const nodeTypes = hasData
    ? [...new Set(data!.nodes.map(n => n.type || 'default'))]
    : []

  return (
    <div className="relative h-full bg-slate-900 overflow-hidden">
      {hasData ? (
        <>
          {/* Graph container */}
          <div ref={containerRef} className="w-full h-full" />

          {/* Controls */}
          <div className="absolute top-4 right-4 flex flex-col gap-1">
            <button
              onClick={toggleAnimation}
              className={`p-2 rounded-lg transition-colors ${isAnimating ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-slate-800 hover:bg-slate-700'
                }`}
              title={isAnimating ? '暂停动画' : '启动动画'}
            >
              {isAnimating ? (
                <Pause className="h-4 w-4 text-white" />
              ) : (
                <Play className="h-4 w-4 text-slate-300" />
              )}
            </button>
            <button
              onClick={handleZoomIn}
              className="p-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              title="放大"
            >
              <ZoomIn className="h-4 w-4 text-slate-300" />
            </button>
            <button
              onClick={handleZoomOut}
              className="p-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              title="缩小"
            >
              <ZoomOut className="h-4 w-4 text-slate-300" />
            </button>
            <button
              onClick={handleFit}
              className="p-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              title="适应屏幕"
            >
              <Maximize2 className="h-4 w-4 text-slate-300" />
            </button>
            <button
              onClick={handleReset}
              className="p-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              title="重新布局"
            >
              <RotateCcw className="h-4 w-4 text-slate-300" />
            </button>
          </div>

          {/* Legend */}
          <div className="absolute bottom-4 left-4 flex flex-wrap gap-2 max-w-[200px]">
            {nodeTypes.map(type => (
              <div key={type} className="flex items-center gap-1.5 px-2 py-1 bg-slate-800 rounded-md">
                <span
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: getNodeColor(type) }}
                />
                <span className="text-xs text-slate-300">{type}</span>
              </div>
            ))}
          </div>

          {/* Stats */}
          <div className="absolute top-4 left-4 px-3 py-2 bg-slate-800 rounded-lg">
            <div className="text-xs text-slate-400">
              <span className="text-slate-200 font-medium">{data!.nodes.length}</span> 节点 ·
              <span className="text-slate-200 font-medium ml-1">{data!.edges.length}</span> 关系
            </div>
          </div>

          {/* Node details panel */}
          {selectedNode && (
            <div className="absolute top-4 right-16 w-64 bg-slate-800 rounded-xl border border-slate-700 shadow-xl overflow-hidden">
              <div className="flex items-center justify-between p-3 border-b border-slate-700">
                <div className="flex items-center gap-2">
                  <span
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: getNodeColor(selectedNode.type) }}
                  />
                  <span className="text-sm font-medium text-white">{selectedNode.label}</span>
                </div>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="p-1 hover:bg-slate-700 rounded transition-colors"
                >
                  <X className="h-4 w-4 text-slate-400" />
                </button>
              </div>

              <div className="p-3 space-y-3">
                <div>
                  <div className="text-xs text-slate-500 mb-1">类型</div>
                  <div className="text-sm text-slate-200">{selectedNode.type}</div>
                </div>

                {Object.entries(selectedNode.properties).filter(([k]) => k !== 'name' && k !== 'type').length > 0 && (
                  <div>
                    <div className="text-xs text-slate-500 mb-1">属性</div>
                    <div className="space-y-1 bg-slate-900/50 p-2 rounded-lg border border-slate-700/50 max-h-40 overflow-y-auto">
                      {Object.entries(selectedNode.properties)
                        .filter(([k]) => k !== 'name' && k !== 'type')
                        .map(([k, v]) => (
                          <div key={k} className="flex flex-col border-b border-slate-700/30 last:border-0 pb-1 mb-1 last:pb-0 last:mb-0">
                            <span className="text-[10px] text-slate-500 uppercase tracking-wider">{k}</span>
                            <span className="text-xs text-slate-300 break-words">{String(v)}</span>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {selectedNode.connections.length > 0 && (
                  <div>
                    <div className="text-xs text-slate-500 mb-2">关系 ({selectedNode.connections.length})</div>
                    <div className="space-y-1.5 max-h-32 overflow-y-auto">
                      {selectedNode.connections.map((conn, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs">
                          <span className={`px-1.5 py-0.5 rounded ${conn.direction === 'out'
                            ? 'bg-emerald-900 text-emerald-400'
                            : 'bg-blue-900 text-blue-400'
                            }`}>
                            {conn.direction === 'out' ? '→' : '←'}
                          </span>
                          <span className="text-slate-400">{String(conn.label)}</span>
                          <span className="text-slate-300 truncate">{String(conn.node)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="flex flex-col items-center justify-center h-full text-center px-4">
          <div className="p-4 rounded-full bg-slate-800 mb-4">
            <svg className="h-8 w-8 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <p className="text-slate-500 text-sm">提问后将在此显示知识图谱</p>
        </div>
      )}
    </div>
  )
}
