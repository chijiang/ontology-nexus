// frontend/src/app/graph/instances/page.tsx
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { AppLayout } from '@/components/layout'
import { InstanceFilter, SearchParams } from '@/components/instance-filter'
import { InstanceGraphViewer } from '@/components/instance-graph-viewer'
import { InstanceDetailPanel } from '@/components/instance-detail-panel'
import { useAuthStore } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import { dataProductsApi } from '@/lib/api'

interface InstanceNode {
    id: string
    name: string
    label: string
    nodeLabel: string
    properties?: Record<string, any>
    color?: string
}

export default function InstancesPage() {
    const router = useRouter()
    const token = useAuthStore((state) => state.token)
    const [isHydrated, setIsHydrated] = useState(false)
    const [searchParams, setSearchParams] = useState<SearchParams | null>(null)
    const [selectedNode, setSelectedNode] = useState<InstanceNode | null>(null)
    const [loading, setLoading] = useState(false)

    const [refreshTrigger, setRefreshTrigger] = useState(0)
    const [syncing, setSyncing] = useState(false)

    useEffect(() => {
        setIsHydrated(true)
    }, [])

    useEffect(() => {
        if (isHydrated && !token) {
            router.push('/')
        }
    }, [isHydrated, token, router])

    if (!isHydrated || !token) {
        return null
    }

    const handleSearch = (params: SearchParams) => {
        setLoading(true)
        setSearchParams(params)
        setSelectedNode(null)
        // 将在 InstanceGraphViewer 中处理加载
        setTimeout(() => setLoading(false), 100)
    }

    const handleUpdate = () => {
        // 触发图谱刷新
        setRefreshTrigger(prev => prev + 1)
    }

    const handleSyncAll = async () => {
        try {
            setSyncing(true)
            toast.info('正在获取数据产品...')

            // 1. 获取所有通过的数据产品
            const res = await dataProductsApi.list(true) // activeOnly = true
            const products = res.data.items || []

            if (products.length === 0) {
                toast.warning('没有找到启用的数据产品')
                setSyncing(false)
                return
            }

            toast.info(`开始同步 ${products.length} 个数据产品...`)

            // 2. 依次触发同步
            let successCount = 0
            let failCount = 0

            for (const product of products) {
                try {
                    toast.loading(`正在同步: ${product.name}...`, { id: `sync-${product.id}` })
                    await dataProductsApi.triggerSync(product.id)
                    toast.success(`同步成功: ${product.name}`, { id: `sync-${product.id}` })
                    successCount++
                } catch (err) {
                    console.error(`Failed to sync product ${product.id}:`, err)
                    toast.error(`同步失败: ${product.name}`, { id: `sync-${product.id}` })
                    failCount++
                }
            }

            // 3. 结果汇总
            if (failCount === 0) {
                toast.success(`所有产品同步完成 (${successCount}/${products.length})`)
            } else {
                toast.warning(`同步完成，但在 ${failCount} 个产品中遇到错误`)
            }

            // 4. 刷新图谱
            handleUpdate()

        } catch (err) {
            console.error('Sync all failed:', err)
            toast.error('同步过程中发生错误')
        } finally {
            setSyncing(false)
        }
    }

    return (
        <AppLayout>
            <div className="h-[calc(100vh-120px)] flex flex-col gap-4">
                {/* 筛选条件和同步按钮区域 */}
                <div className="flex flex-col md:flex-row gap-4 items-start">
                    <div className="flex-1 w-full">
                        <InstanceFilter onSearch={handleSearch} loading={loading} />
                    </div>
                    <Button
                        onClick={handleSyncAll}
                        disabled={syncing}
                        className="w-full md:w-auto shrink-0 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-md"
                    >
                        <RefreshCw className={`mr-2 h-4 w-4 ${syncing ? 'animate-spin' : ''}`} />
                        {syncing ? '同步中...' : '一键同步'}
                    </Button>
                </div>

                {/* 图谱和详情区域 */}
                <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 min-h-0">
                    {/* 实例图谱 */}
                    <div className={`bg-white rounded-lg border overflow-hidden ${selectedNode ? 'lg:col-span-2' : 'lg:col-span-3'}`}>
                        <InstanceGraphViewer
                            searchParams={searchParams}
                            onNodeSelect={setSelectedNode}
                            refreshTrigger={refreshTrigger}
                        />
                    </div>

                    {/* 实例详情面板 */}
                    {selectedNode && (
                        <div className="lg:col-span-1">
                            <InstanceDetailPanel
                                node={selectedNode}
                                onClose={() => setSelectedNode(null)}
                                onUpdate={handleUpdate}
                            />
                        </div>
                    )}
                </div>
            </div>
        </AppLayout>
    )
}
