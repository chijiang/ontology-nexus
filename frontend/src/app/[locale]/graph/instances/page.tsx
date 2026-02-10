// frontend/src/app/graph/instances/page.tsx
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
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
    const t = useTranslations()
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
        // Will be handled in InstanceGraphViewer
        setTimeout(() => setLoading(false), 100)
    }

    const handleUpdate = () => {
        // Trigger graph refresh
        setRefreshTrigger(prev => prev + 1)
    }

    const handleSyncAll = async () => {
        try {
            setSyncing(true)
            toast.info(t('graph.instances.fetchingProducts'))

            // 1. Get all enabled data products
            const res = await dataProductsApi.list(true) // activeOnly = true
            const products = res.data.items || []

            if (products.length === 0) {
                toast.warning(t('graph.instances.noActiveProducts'))
                setSyncing(false)
                return
            }

            toast.info(t('graph.instances.startSync', { count: products.length }))

            // 2. Trigger sync for each
            let successCount = 0
            let failCount = 0

            for (const product of products) {
                try {
                    toast.loading(t('graph.instances.syncingProduct', { name: product.name }), { id: `sync-${product.id}` })
                    await dataProductsApi.triggerSync(product.id)
                    toast.success(t('graph.instances.syncSuccess', { name: product.name }), { id: `sync-${product.id}` })
                    successCount++
                } catch (err) {
                    console.error(`Failed to sync product ${product.id}:`, err)
                    toast.error(t('graph.instances.syncFailed', { name: product.name }), { id: `sync-${product.id}` })
                    failCount++
                }
            }

            // 3. Summary
            if (failCount === 0) {
                toast.success(t('graph.instances.syncComplete', { success: successCount, total: products.length }))
            } else {
                toast.warning(t('graph.instances.syncPartialFailed', { count: failCount }))
            }

            // 4. Refresh graph
            handleUpdate()

        } catch (err) {
            console.error('Sync all failed:', err)
            toast.error(t('graph.instances.syncError'))
        } finally {
            setSyncing(false)
        }
    }

    return (
        <AppLayout>
            <div className="h-[calc(100vh-120px)] flex flex-col gap-4">
                {/* Filter and sync button area */}
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
                        {syncing ? t('graph.instances.syncing') : t('graph.instances.oneClickSync')}
                    </Button>
                </div>

                {/* Graph and details area */}
                <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 min-h-0">
                    {/* Instance graph */}
                    <div className={`bg-white rounded-lg border overflow-hidden ${selectedNode ? 'lg:col-span-2' : 'lg:col-span-3'}`}>
                        <InstanceGraphViewer
                            searchParams={searchParams}
                            onNodeSelect={setSelectedNode}
                            refreshTrigger={refreshTrigger}
                        />
                    </div>

                    {/* Instance details panel */}
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
