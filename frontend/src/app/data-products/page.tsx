'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
    Server,
    Plus,
    RefreshCw,
    Trash2,
    Settings,
    CheckCircle,
    XCircle,
    AlertCircle,
    Link2,
    Clock
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle
} from '@/components/ui/card'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { toast } from 'sonner'
import { AppLayout } from '@/components/layout'
import { dataProductsApi, DataProduct, ConnectionStatus } from '@/lib/api'

function ConnectionStatusBadge({ status }: { status: ConnectionStatus }) {
    const config = {
        connected: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-500/10', label: '已连接' },
        disconnected: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/10', label: '已断开' },
        error: { icon: AlertCircle, color: 'text-orange-500', bg: 'bg-orange-500/10', label: '错误' },
        unknown: { icon: AlertCircle, color: 'text-gray-500', bg: 'bg-gray-500/10', label: '未知' },
    }

    const { icon: Icon, color, bg, label } = config[status] || config.unknown

    return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${bg} ${color}`}>
            <Icon className="w-3.5 h-3.5" />
            {label}
        </span>
    )
}

export default function DataProductsPage() {
    const router = useRouter()
    const [isHydrated, setIsHydrated] = useState(false)
    const token = localStorage.getItem('auth-storage')

    const [products, setProducts] = useState<DataProduct[]>([])
    const [loading, setLoading] = useState(true)
    const [createDialogOpen, setCreateDialogOpen] = useState(false)
    const [testingConnection, setTestingConnection] = useState<number | null>(null)
    const [deletingProduct, setDeletingProduct] = useState<number | null>(null)

    // Schema editing
    const [schemaDialogOpen, setSchemaDialogOpen] = useState(false)
    const [selectedProductForSchema, setSelectedProductForSchema] = useState<DataProduct | null>(null)
    const [schemaContent, setSchemaContent] = useState('')
    const [savingSchema, setSavingSchema] = useState(false)

    const handleOpenSchema = (product: any) => {
        setSelectedProductForSchema(product)
        setSchemaContent(product.proto_content || '')
        setSchemaDialogOpen(true)
    }

    const handleSaveSchema = async () => {
        if (!selectedProductForSchema) return
        setSavingSchema(true)
        try {
            await dataProductsApi.update(selectedProductForSchema.id, {
                proto_content: schemaContent
            })
            toast.success('Schema 已保存', { description: 'Proto 定义更新成功' })
            setSchemaDialogOpen(false)
            loadProducts()
        } catch (err) {
            toast.error('保存失败')
        } finally {
            setSavingSchema(false)
        }
    }

    // Form state
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        grpc_host: 'localhost',
        grpc_port: 50051,
        service_name: '',
    })
    const [creating, setCreating] = useState(false)

    const loadProducts = async () => {
        try {
            setLoading(true)
            const response = await dataProductsApi.list()
            setProducts(response.data.items)
        } catch (error) {
            toast.error('加载失败', {
                description: '无法加载数据产品列表',
            })
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        setIsHydrated(true)
        loadProducts()
    }, [])

    useEffect(() => {
        if (isHydrated && !token) {
            router.push('/')
        }
    }, [isHydrated, token, router])

    if (!isHydrated || !token) {
        return null
    }

    const handleCreate = async () => {
        if (!formData.name || !formData.grpc_host || !formData.service_name) {
            toast.error('验证失败', {
                description: '请填写必填字段',
            })
            return
        }

        try {
            setCreating(true)
            await dataProductsApi.create(formData)
            toast.success('创建成功', {
                description: `数据产品 "${formData.name}" 已创建`,
            })
            setCreateDialogOpen(false)
            setFormData({
                name: '',
                description: '',
                grpc_host: 'localhost',
                grpc_port: 50051,
                service_name: '',
            })
            loadProducts()
        } catch (error: any) {
            toast.error('创建失败', {
                description: error.response?.data?.detail || '请检查输入',
            })
        } finally {
            setCreating(false)
        }
    }

    const handleTestConnection = async (productId: number) => {
        try {
            setTestingConnection(productId)
            const response = await dataProductsApi.testConnection(productId)
            const result = response.data

            if (result.success) {
                toast.success('连接成功', {
                    description: `延迟: ${result.latency_ms}ms`,
                })
            } else {
                toast.error('连接失败', {
                    description: result.message,
                })
            }

            loadProducts() // Refresh to get updated status
        } catch (error: any) {
            toast.error('测试失败', {
                description: error.response?.data?.detail || '连接测试出错',
            })
        } finally {
            setTestingConnection(null)
        }
    }

    const handleDelete = async (productId: number) => {
        if (!confirm('确定要删除此数据产品吗？所有相关的映射配置也会被删除。')) {
            return
        }

        try {
            setDeletingProduct(productId)
            await dataProductsApi.delete(productId)
            toast.success('删除成功', {
                description: '数据产品已删除',
            })
            loadProducts()
        } catch (error: any) {
            toast.error('删除失败', {
                description: error.response?.data?.detail || '删除出错',
            })
        } finally {
            setDeletingProduct(null)
        }
    }

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '-'
        return new Date(dateStr).toLocaleString('zh-CN', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        })
    }

    return (
        <AppLayout>
            <div className="container mx-auto py-8 px-4 max-w-6xl">
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight">数据产品</h1>
                        <p className="text-muted-foreground mt-1">
                            注册和管理 gRPC 数据服务，配置与 Ontology 的映射关系
                        </p>
                    </div>

                    <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
                        <DialogTrigger asChild>
                            <Button>
                                <Plus className="w-4 h-4 mr-2" />
                                注册数据产品
                            </Button>
                        </DialogTrigger>
                        <DialogContent className="sm:max-w-[500px]">
                            <DialogHeader>
                                <DialogTitle>注册新数据产品</DialogTitle>
                                <DialogDescription>
                                    配置 gRPC 服务端点信息，注册后可进行数据映射
                                </DialogDescription>
                            </DialogHeader>

                            <div className="grid gap-4 py-4">
                                <div className="grid gap-2">
                                    <Label htmlFor="name">产品名称 *</Label>
                                    <Input
                                        id="name"
                                        placeholder="例如: ERP-Supplier"
                                        value={formData.name}
                                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    />
                                </div>

                                <div className="grid gap-2">
                                    <Label htmlFor="description">描述</Label>
                                    <Textarea
                                        id="description"
                                        placeholder="数据产品的简要描述"
                                        value={formData.description}
                                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    />
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div className="grid gap-2">
                                        <Label htmlFor="host">gRPC 服务地址 *</Label>
                                        <Input
                                            id="host"
                                            placeholder="localhost"
                                            value={formData.grpc_host}
                                            onChange={(e) => setFormData({ ...formData, grpc_host: e.target.value })}
                                        />
                                    </div>
                                    <div className="grid gap-2">
                                        <Label htmlFor="port">端口 *</Label>
                                        <Input
                                            id="port"
                                            type="number"
                                            placeholder="50051"
                                            value={formData.grpc_port}
                                            onChange={(e) => setFormData({ ...formData, grpc_port: parseInt(e.target.value) || 50051 })}
                                        />
                                    </div>
                                </div>

                                <div className="grid gap-2">
                                    <Label htmlFor="service">服务名称 *</Label>
                                    <Input
                                        id="service"
                                        placeholder="例如: SupplierService"
                                        value={formData.service_name}
                                        onChange={(e) => setFormData({ ...formData, service_name: e.target.value })}
                                    />
                                </div>
                            </div>

                            <DialogFooter>
                                <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
                                    取消
                                </Button>
                                <Button onClick={handleCreate} disabled={creating}>
                                    {creating ? '创建中...' : '创建'}
                                </Button>
                            </DialogFooter>
                        </DialogContent>
                    </Dialog>

                    {/* Schema Edit Dialog */}
                    <Dialog open={schemaDialogOpen} onOpenChange={setSchemaDialogOpen}>
                        <DialogContent className="max-w-4xl h-[80vh] flex flex-col">
                            <DialogHeader>
                                <DialogTitle>编辑 Proto Schema - {selectedProductForSchema?.name}</DialogTitle>
                                <DialogDescription>
                                    手动编辑此数据产品的 gRPC 服务定义 (.proto)。这有助于在没有反射支持的情况下识别 Message 类型和同步方法。
                                </DialogDescription>
                            </DialogHeader>
                            <div className="flex-1 min-h-0 mt-4">
                                <textarea
                                    className="w-full h-full p-4 font-mono text-sm bg-slate-900 text-slate-100 rounded-lg border-none focus:ring-1 focus:ring-primary resize-none"
                                    placeholder="// Paste your .proto file content here..."
                                    value={schemaContent}
                                    onChange={(e) => setSchemaContent(e.target.value)}
                                />
                            </div>
                            <DialogFooter className="mt-4">
                                <Button variant="outline" onClick={() => setSchemaDialogOpen(false)}>
                                    取消
                                </Button>
                                <Button onClick={handleSaveSchema} disabled={savingSchema}>
                                    {savingSchema ? (
                                        <>
                                            <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                                            保存中...
                                        </>
                                    ) : '保存 Schema'}
                                </Button>
                            </DialogFooter>
                        </DialogContent>
                    </Dialog>
                </div>

                {/* Product List */}
                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
                    </div>
                ) : products.length === 0 ? (
                    <Card className="border-dashed">
                        <CardContent className="flex flex-col items-center justify-center py-12">
                            <Server className="w-12 h-12 text-muted-foreground mb-4" />
                            <h3 className="text-lg font-medium mb-2">暂无数据产品</h3>
                            <p className="text-muted-foreground text-sm mb-4">
                                注册第一个 gRPC 数据产品以开始数据映射
                            </p>
                            <Button onClick={() => setCreateDialogOpen(true)}>
                                <Plus className="w-4 h-4 mr-2" />
                                注册数据产品
                            </Button>
                        </CardContent>
                    </Card>
                ) : (
                    <div className="grid gap-4">
                        {products.map((product) => (
                            <Card key={product.id} className="hover:shadow-md transition-shadow">
                                <CardHeader className="pb-3">
                                    <div className="flex items-start justify-between">
                                        <div className="flex items-center gap-3">
                                            <div className="p-2 bg-primary/10 rounded-lg">
                                                <Server className="w-5 h-5 text-primary" />
                                            </div>
                                            <div>
                                                <CardTitle className="text-lg">{product.name}</CardTitle>
                                                <CardDescription className="mt-0.5">
                                                    {product.grpc_host}:{product.grpc_port} / {product.service_name}
                                                </CardDescription>
                                            </div>
                                        </div>

                                        <ConnectionStatusBadge status={product.connection_status} />
                                    </div>
                                </CardHeader>

                                <CardContent>
                                    {product.description && (
                                        <p className="text-sm text-muted-foreground mb-4">
                                            {product.description}
                                        </p>
                                    )}

                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                            <span className="flex items-center gap-1">
                                                <Clock className="w-3.5 h-3.5" />
                                                上次检查: {formatDate(product.last_health_check)}
                                            </span>
                                            {product.last_error && (
                                                <span className="text-red-500">
                                                    错误: {product.last_error}
                                                </span>
                                            )}
                                        </div>

                                        <div className="flex items-center gap-2">
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => handleTestConnection(product.id)}
                                                disabled={testingConnection === product.id}
                                            >
                                                <RefreshCw className={`w-4 h-4 mr-1.5 ${testingConnection === product.id ? 'animate-spin' : ''}`} />
                                                测试连接
                                            </Button>

                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => handleOpenSchema(product)}
                                            >
                                                <Settings className="w-4 h-4 mr-1.5" />
                                                Schema
                                            </Button>

                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => router.push(`/data-products/${product.id}/mappings`)}
                                            >
                                                <Link2 className="w-4 h-4 mr-1.5" />
                                                配置映射
                                            </Button>

                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => handleDelete(product.id)}
                                                disabled={deletingProduct === product.id}
                                                className="text-red-500 hover:text-red-600 hover:bg-red-50"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </Button>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                )}
            </div>
        </AppLayout>
    )
}
