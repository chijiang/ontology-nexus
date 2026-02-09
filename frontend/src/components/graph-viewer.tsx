// frontend/src/components/graph-viewer.tsx
'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import cytoscape, { Core, ElementDefinition } from 'cytoscape'
import { graphApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react'

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

export function GraphViewer() {
  const token = useAuthStore((state) => state.token)
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)
  const [selectedNode, setSelectedNode] = useState<any>(null)
  const [isMounted, setIsMounted] = useState(true)

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
            'width': 65,
            'height': 65,
            'font-size': 12,
            'font-weight': 500,
            'text-wrap': 'ellipsis',
            'text-max-width': '60px',
            'border-width': 3,
            'border-color': 'data(borderColor)',
            'text-outline-color': 'data(color)',
            'text-outline-width': 2,
          },
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 4,
            'border-color': '#FFD700',
            'width': 75,
            'height': 75,
          },
        },
        {
          selector: 'node:active',
          style: {
            'overlay-opacity': 0.1,
            'overlay-color': '#000',
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
            'color': '#333',
            'text-background-color': '#fff',
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
            'line-color': '#FFD700',
            'target-arrow-color': '#FFD700',
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
      setSelectedNode(node.data())
    })

    // 单击空白处取消选中
    cyRef.current.on('tap', (evt) => {
      if (evt.target === cyRef.current) {
        setSelectedNode(null)
      }
    })

    return () => {
      cyRef.current?.destroy()
      cyRef.current = null
    }
  }, [])

  // Load initial graph on mount
  useEffect(() => {
    if (token && cyRef.current) {
      loadInitialGraph()
    }
  }, [token])

  const loadInitialGraph = async () => {
    // Early return if cytoscape is not ready
    if (!cyRef.current || !isMounted) return

    try {
      const res = await graphApi.getStatistics(token!)
      const stats = res.data

      // 从统计数据中获取标签，然后搜索一些初始节点
      const elements: ElementDefinition[] = []
      const addedNodes = new Set<string>()

      // 使用标签分布来加载初始节点
      if (stats.label_distribution) {
        for (const item of stats.label_distribution.slice(0, 5)) {
          const labels = item.labels || []
          // 跳过 Schema 节点
          if (labels.includes('__Schema')) continue

          const labelName = labels[0]
          if (!labelName) continue

          // 搜索该类型的节点
          try {
            const nodesRes = await graphApi.getNodesByLabel(labelName, 10, token!)
            const nodes = nodesRes.data
            const nodeColor = getColorForLabel(labelName)
            const borderColor = shadeColor(nodeColor, -20)

            nodes.forEach((n: any) => {
              if (!addedNodes.has(n.name)) {
                elements.push({
                  data: {
                    id: n.name,
                    label: n.name,
                    nodeLabel: labelName,
                    color: nodeColor,
                    borderColor: borderColor,
                  },
                })
                addedNodes.add(n.name)
              }
            })
          } catch (err) {
            console.error(`Failed to fetch nodes for label ${labelName}:`, err)
          }
        }
      }

      // 如果没有找到节点，添加一个提示节点
      if (elements.length === 0) {
        elements.push({
          data: {
            id: 'empty',
            label: '暂无数据',
            color: '#888',
            borderColor: '#666',
          },
        })
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
      console.error('Failed to load graph:', err)
      // 显示错误提示节点
      if (cyRef.current && isMounted) {
        cyRef.current.json({
          elements: [{
            data: {
              id: 'error',
              label: '加载失败',
              color: '#F16667',
              borderColor: '#C44',
            }
          }],
        })
      }
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
              color: nodeColor,
              borderColor: borderColor,
            },
          })
        }

        // Add edges
        n.relationships?.forEach((rel: any, i: number) => {
          // Use relationship ID if available, otherwise fallback to composite key
          const edgeId = rel.id
            ? `rel-${rel.id}`
            : (typeof rel === 'object' ? `${rel.source}-${rel.target}-${rel.type}` : `${nodeName}-${n.name}-${i}`)

          // Check both cytoscape and current batch to avoid duplicates
          if (!cyRef.current?.getElementById(edgeId).length && !addedEdgeIds.has(edgeId)) {
            addedEdgeIds.add(edgeId)
            newElements.push({
              data: {
                id: edgeId,
                source: typeof rel === 'object' ? rel.source : nodeName,
                target: typeof rel === 'object' ? rel.target : n.name,
                label: typeof rel === 'object' ? rel.type : rel,
              },
            })
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

      {/* Legend */}
      {/* 标题 */}
      <div className="absolute top-2 left-2 z-10 bg-white/90 px-3 py-1 rounded-lg shadow text-sm font-semibold text-emerald-700">
        🔗 Instance Data
      </div>

      <div className="absolute bottom-4 left-4 z-10 bg-white/95 p-3 rounded-lg shadow-lg">
        <h4 className="text-xs font-semibold mb-2 text-gray-600">节点类型</h4>
        <div className="flex flex-wrap gap-2">
          {Array.from(labelColorMap.entries()).map(([label, color]) => (
            <div key={label} className="flex items-center gap-1">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span className="text-xs text-gray-700">{label}</span>
            </div>
          ))}
        </div>
      </div>

      {selectedNode && (
        <div className="absolute top-4 right-4 z-10 bg-white/95 backdrop-blur p-4 rounded-lg shadow-lg max-w-xs border border-gray-200">
          <div className="flex items-center gap-2 mb-2">
            <div
              className="w-4 h-4 rounded-full"
              style={{ backgroundColor: selectedNode.color }}
            />
            <h3 className="font-semibold text-gray-800">{selectedNode.nodeLabel || '节点'}</h3>
          </div>
          <p className="text-sm text-gray-600 mb-3">
            <span className="font-medium">名称:</span> {selectedNode.label}
          </p>
          <Button
            size="sm"
            className="w-full"
            style={{ backgroundColor: selectedNode.color }}
            onClick={() => expandNode(selectedNode.id)}
          >
            展开邻居
          </Button>
        </div>
      )}

      <div ref={containerRef} className="w-full h-full" style={{ background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)' }} />
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
