// frontend/src/components/graph-preview.tsx
'use client'

import { useEffect, useRef, useCallback, useState } from 'react'
import cytoscape, { Core, NodeSingular } from 'cytoscape'
import { X, ZoomIn, ZoomOut, Maximize2, RotateCcw, Play, Pause, Network } from 'lucide-react'

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
    'PurchaseOrder': '#A100FF',
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
            'color': '#334155',
            'width': 45,
            'height': 45,
            'font-size': 11,
            'font-weight': 500,
            'text-wrap': 'ellipsis',
            'text-max-width': '100px',
            'border-width': 2,
            'border-color': '#cbd5e1',
            'transition-property': 'width, height, border-width, border-color',
            'transition-duration': 150,
          },
        },
        {
          selector: 'node:selected',
          style: {
            'border-color': '#A100FF',
            'border-width': 3,
            'width': 50,
            'height': 50,
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
            'width': 1.5,
            'line-color': '#94a3b8',
            'target-arrow-color': '#94a3b8',
            'target-arrow-shape': 'triangle',
            'arrow-scale': 1.2,
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': 9,
            'color': '#64748b',
            'text-rotation': 'autorotate',
            'text-margin-y': -10,
            'text-background-color': '#ffffff',
            'text-background-opacity': 0.9,
            'text-background-padding': '3px',
          },
        },
        {
          selector: 'edge:selected',
          style: {
            'line-color': '#A100FF',
            'target-arrow-color': '#A100FF',
            'width': 2.5,
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
    <div className="relative h-full bg-white overflow-hidden">
      {hasData ? (
        <>
          {/* Graph container */}
          <div ref={containerRef} className="w-full h-full" />

          {/* Controls */}
          <div className="absolute top-4 right-4 flex flex-col gap-1">
            <button
              onClick={toggleAnimation}
              className={`p-2 rounded-lg transition-colors ${isAnimating ? 'bg-primary hover:opacity-90' : 'bg-slate-100 hover:bg-slate-200'
                }`}
              title={isAnimating ? '暂停动画' : '启动动画'}
            >
              {isAnimating ? (
                <Pause className="h-4 w-4 text-white" />
              ) : (
                <Play className="h-4 w-4 text-slate-600" />
              )}
            </button>
            <button
              onClick={handleZoomIn}
              className="p-2 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
              title="放大"
            >
              <ZoomIn className="h-4 w-4 text-slate-600" />
            </button>
            <button
              onClick={handleZoomOut}
              className="p-2 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
              title="缩小"
            >
              <ZoomOut className="h-4 w-4 text-slate-600" />
            </button>
            <button
              onClick={handleFit}
              className="p-2 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
              title="适应屏幕"
            >
              <Maximize2 className="h-4 w-4 text-slate-600" />
            </button>
            <button
              onClick={handleReset}
              className="p-2 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
              title="重新布局"
            >
              <RotateCcw className="h-4 w-4 text-slate-600" />
            </button>
          </div>

          {/* Legend */}
          <div className="absolute bottom-4 left-4 flex flex-wrap gap-2 max-w-[200px]">
            {nodeTypes.map(type => (
              <div key={type} className="flex items-center gap-1.5 px-2 py-1 bg-white border border-slate-200 rounded-md shadow-sm">
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: getNodeColor(type) }}
                />
                <span className="text-[10px] font-medium text-slate-600">{type}</span>
              </div>
            ))}
          </div>

          {/* Stats */}
          <div className="absolute top-4 left-4 px-3 py-1.5 bg-white border border-slate-200 rounded-lg shadow-sm">
            <div className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">
              <span className="text-primary font-bold">{data!.nodes.length}</span> 节点 ·
              <span className="text-primary font-bold ml-1">{data!.edges.length}</span> 关系
            </div>
          </div>

          {/* Node details panel */}
          {selectedNode && (
            <div className="absolute top-4 right-16 w-64 bg-white rounded-xl border border-slate-200 shadow-xl overflow-hidden ring-1 ring-black/5">
              <div className="flex items-center justify-between p-3 border-b border-slate-100 bg-slate-50/50">
                <div className="flex items-center gap-2">
                  <span
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: getNodeColor(selectedNode.type) }}
                  />
                  <span className="text-sm font-semibold text-slate-800">{selectedNode.label}</span>
                </div>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="p-1 hover:bg-slate-200 rounded transition-colors"
                >
                  <X className="h-4 w-4 text-slate-400" />
                </button>
              </div>

              <div className="p-3 space-y-3">
                <div>
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">类型</div>
                  <div className="text-sm font-medium text-slate-700">{selectedNode.type}</div>
                </div>

                {Object.entries(selectedNode.properties).filter(([k]) => k !== 'name' && k !== 'type').length > 0 && (
                  <div>
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">属性</div>
                    <div className="space-y-1 bg-slate-50 p-2 rounded-lg border border-slate-100 max-h-40 overflow-y-auto">
                      {Object.entries(selectedNode.properties)
                        .filter(([k]) => k !== 'name' && k !== 'type')
                        .map(([k, v]) => (
                          <div key={k} className="flex flex-col border-b border-slate-200/50 last:border-0 pb-1 mb-1 last:pb-0 last:mb-0">
                            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter">{k}</span>
                            <span className="text-xs text-slate-600 break-words font-medium">{String(v)}</span>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {selectedNode.connections.length > 0 && (
                  <div>
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">关系 ({selectedNode.connections.length})</div>
                    <div className="space-y-1.5 max-h-32 overflow-y-auto">
                      {selectedNode.connections.map((conn, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs">
                          <span className={`px-1.5 py-0.5 rounded font-bold ${conn.direction === 'out'
                            ? 'bg-primary/10 text-primary'
                            : 'bg-slate-100 text-slate-600'
                            }`}>
                            {conn.direction === 'out' ? '→' : '←'}
                          </span>
                          <span className="text-slate-400 text-[10px]">{String(conn.label)}</span>
                          <span className="text-slate-600 truncate font-medium">{String(conn.node)}</span>
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
          <div className="p-4 rounded-full bg-slate-50 mb-4 border border-slate-100">
            <Network className="h-8 w-8 text-primary/40" />
          </div>
          <p className="text-slate-400 text-sm font-medium uppercase tracking-wider">提问后将在此显示知识图谱</p>
        </div>
      )}
    </div>
  )
}
