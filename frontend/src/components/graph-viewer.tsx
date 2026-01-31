// frontend/src/components/graph-viewer.tsx
'use client'

import { useEffect, useRef, useState } from 'react'
import cytoscape, { Core, ElementDefinition } from 'cytoscape'
import { graphApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react'

export function GraphViewer() {
  const token = useAuthStore((state) => state.token)
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)
  const [selectedNode, setSelectedNode] = useState<any>(null)

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
            'background-color': '#4F46E5',
            'color': '#fff',
            'width': '50px',
            'height': '50px',
            'text-wrap': 'wrap',
            'text-max-width': '80px',
          },
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 3,
            'border-color': '#F59E0B',
          },
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#94a3b8',
            'target-arrow-color': '#94a3b8',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'text-rotation': 'autorotate',
            'text-margin-y': -10,
          },
        },
      ],
      layout: {
        name: 'concentric',
      },
    })

    // 双击展开邻居
    cyRef.current.on('dblclick', 'node', async (evt) => {
      const node = evt.target
      const uri = node.data('id')
      await expandNode(uri)
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
    }
  }, [])

  const loadInitialGraph = async () => {
    try {
      const res = await graphApi.getStatistics(token!)
      // 这里简化处理，实际应该根据统计数据加载初始节点
      const elements: ElementDefinition[] = [
        { data: { id: 'demo1', label: '示例节点1' } },
        { data: { id: 'demo2', label: '示例节点2' } },
        { data: { id: 'e1', source: 'demo1', target: 'demo2', label: '关系' } },
      ]
      cyRef.current?.json({ elements })
      cyRef.current?.layout({ name: 'concentric' }).run()
    } catch (err) {
      console.error('Failed to load graph:', err)
    }
  }

  const expandNode = async (uri: string) => {
    try {
      const res = await graphApi.getNeighbors(uri, 1, token!)
      const neighbors = res.data

      const newNodes = neighbors.map((n: any) => ({
        data: { id: n.uri, label: n.name },
      }))

      const newEdges = neighbors.flatMap((n: any) =>
        n.relationships?.map((rel: string, i: number) => ({
          data: {
            id: `${uri}-${n.uri}-${i}`,
            source: uri,
            target: n.uri,
            label: rel,
          },
        })) || []
      )

      cyRef.current?.add([...newNodes, ...newEdges])
      cyRef.current?.layout({ name: 'concentric' }).run()
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
        <Button size="icon" variant="secondary" onClick={handleZoomIn}>
          <ZoomIn className="h-4 w-4" />
        </Button>
        <Button size="icon" variant="secondary" onClick={handleZoomOut}>
          <ZoomOut className="h-4 w-4" />
        </Button>
        <Button size="icon" variant="secondary" onClick={handleFit}>
          <Maximize2 className="h-4 w-4" />
        </Button>
      </div>

      {selectedNode && (
        <div className="absolute top-4 right-4 z-10 bg-white p-4 rounded-lg shadow-lg max-w-xs">
          <h3 className="font-semibold">节点详情</h3>
          <p className="text-sm">URI: {selectedNode.id}</p>
          <p className="text-sm">名称: {selectedNode.label}</p>
          <Button
            size="sm"
            variant="outline"
            className="mt-2"
            onClick={() => expandNode(selectedNode.id)}
          >
            展开邻居
          </Button>
        </div>
      )}

      <div ref={containerRef} className="w-full h-full bg-gray-50" />
    </div>
  )
}
