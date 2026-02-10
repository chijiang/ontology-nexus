'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations, useLocale } from 'next-intl'
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
    const t = useTranslations()
    const config = {
        connected: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-500/10', label: t('dataProducts.connecting') },
        disconnected: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/10', label: t('dataProducts.disconnected') },
        error: { icon: AlertCircle, color: 'text-orange-500', bg: 'bg-orange-500/10', label: t('dataProducts.connectionError') },
        unknown: { icon: AlertCircle, color: 'text-gray-500', bg: 'bg-gray-500/10', label: t('dataProducts.connectionUnknown') },
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
    const locale = useLocale()
    const t = useTranslations()
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
            toast.success(t('dataProducts.schemaSaved'), { description: t('dataProducts.schemaSavedDesc') })
            setSchemaDialogOpen(false)
            loadProducts()
        } catch (err) {
            toast.error(t('dataProducts.saveFailed'))
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
            toast.error(t('dataProducts.loadFailed'), {
                description: t('dataProducts.loadFailedDesc'),
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
            router.push(`/${locale}`)
        }
    }, [isHydrated, token, router, locale])

    if (!isHydrated || !token) {
        return null
    }

    const handleCreate = async () => {
        if (!formData.name || !formData.grpc_host || !formData.service_name) {
            toast.error(t('dataProducts.validationFailed'), {
                description: t('dataProducts.fillRequired'),
            })
            return
        }

        try {
            setCreating(true)
            await dataProductsApi.create(formData)
            toast.success(t('dataProducts.createSuccess'), {
                description: t('dataProducts.createSuccessDesc', { name: formData.name }),
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
            toast.error(t('dataProducts.createFailed'), {
                description: error.response?.data?.detail || t('dataProducts.createFailedDesc'),
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
                toast.success(t('dataProducts.connectionSuccess'), {
                    description: result.latency_ms ? t('dataProducts.latency', { ms: result.latency_ms }) : undefined,
                })
            } else {
                toast.error(t('dataProducts.connectionFailed'), {
                    description: result.message,
                })
            }

            loadProducts() // Refresh to get updated status
        } catch (error: any) {
            toast.error(t('dataProducts.testFailed'), {
                description: error.response?.data?.detail || t('dataProducts.testFailedDesc'),
            })
        } finally {
            setTestingConnection(null)
        }
    }

    const handleDelete = async (productId: number) => {
        if (!confirm(t('dataProducts.deleteConfirm'))) {
            return
        }

        try {
            setDeletingProduct(productId)
            await dataProductsApi.delete(productId)
            toast.success(t('dataProducts.deleteSuccess'), {
                description: t('dataProducts.deleteSuccessDesc'),
            })
            loadProducts()
        } catch (error: any) {
            toast.error(t('dataProducts.deleteFailed'), {
                description: error.response?.data?.detail || t('dataProducts.deleteFailedDesc'),
            })
        } finally {
            setDeletingProduct(null)
        }
    }

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '-'
        return new Date(dateStr).toLocaleString(locale === 'zh' ? 'zh-CN' : 'en-US', {
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
                        <h1 className="text-3xl font-bold tracking-tight">{t('dataProducts.title')}</h1>
                        <p className="text-muted-foreground mt-1">
                            {t('dataProducts.description')}
                        </p>
                    </div>

                    <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
                        <DialogTrigger asChild>
                            <Button>
                                <Plus className="w-4 h-4 mr-2" />
                                {t('dataProducts.register')}
                            </Button>
                        </DialogTrigger>
                        <DialogContent className="sm:max-w-[500px]">
                            <DialogHeader>
                                <DialogTitle>{t('dataProducts.registerNew')}</DialogTitle>
                                <DialogDescription>
                                    {t('dataProducts.registerDesc')}
                                </DialogDescription>
                            </DialogHeader>

                            <div className="grid gap-4 py-4">
                                <div className="grid gap-2">
                                    <Label htmlFor="name">{t('dataProducts.productName')} *</Label>
                                    <Input
                                        id="name"
                                        placeholder={t('dataProducts.productNamePlaceholder')}
                                        value={formData.name}
                                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    />
                                </div>

                                <div className="grid gap-2">
                                    <Label htmlFor="description">{t('dataProducts.desc')}</Label>
                                    <Textarea
                                        id="description"
                                        placeholder={t('dataProducts.descPlaceholder')}
                                        value={formData.description}
                                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    />
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div className="grid gap-2">
                                        <Label htmlFor="host">{t('dataProducts.host')} *</Label>
                                        <Input
                                            id="host"
                                            placeholder={t('dataProducts.hostPlaceholder')}
                                            value={formData.grpc_host}
                                            onChange={(e) => setFormData({ ...formData, grpc_host: e.target.value })}
                                        />
                                    </div>
                                    <div className="grid gap-2">
                                        <Label htmlFor="port">{t('dataProducts.port')} *</Label>
                                        <Input
                                            id="port"
                                            type="number"
                                            placeholder={t('dataProducts.portPlaceholder')}
                                            value={formData.grpc_port}
                                            onChange={(e) => setFormData({ ...formData, grpc_port: parseInt(e.target.value) || 50051 })}
                                        />
                                    </div>
                                </div>

                                <div className="grid gap-2">
                                    <Label htmlFor="service">{t('dataProducts.serviceName')} *</Label>
                                    <Input
                                        id="service"
                                        placeholder={t('dataProducts.serviceNamePlaceholder')}
                                        value={formData.service_name}
                                        onChange={(e) => setFormData({ ...formData, service_name: e.target.value })}
                                    />
                                </div>
                            </div>

                            <DialogFooter>
                                <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
                                    {t('common.cancel')}
                                </Button>
                                <Button onClick={handleCreate} disabled={creating}>
                                    {creating ? t('common.loading') : t('common.create')}
                                </Button>
                            </DialogFooter>
                        </DialogContent>
                    </Dialog>

                    {/* Schema Edit Dialog */}
                    <Dialog open={schemaDialogOpen} onOpenChange={setSchemaDialogOpen}>
                        <DialogContent className="max-w-4xl h-[80vh] flex flex-col">
                            <DialogHeader>
                                <DialogTitle>{t('dataProducts.schemaTitle', { name: selectedProductForSchema?.name || '' })}</DialogTitle>
                                <DialogDescription>
                                    {t('dataProducts.schemaDesc')}
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
                                    {t('common.cancel')}
                                </Button>
                                <Button onClick={handleSaveSchema} disabled={savingSchema}>
                                    {savingSchema ? (
                                        <>
                                            <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                                            {t('dataProducts.saving')}
                                        </>
                                    ) : t('dataProducts.saveSchema')}
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
                            <h3 className="text-lg font-medium mb-2">{t('dataProducts.noProducts')}</h3>
                            <p className="text-muted-foreground text-sm mb-4">
                                {t('dataProducts.noProductsDesc')}
                            </p>
                            <Button onClick={() => setCreateDialogOpen(true)}>
                                <Plus className="w-4 h-4 mr-2" />
                                {t('dataProducts.register')}
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
                                                {t('dataProducts.lastCheck')}: {formatDate(product.last_health_check)}
                                            </span>
                                            {product.last_error && (
                                                <span className="text-red-500">
                                                    {t('dataProducts.lastError')}: {product.last_error}
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
                                                {t('dataProducts.testConnection')}
                                            </Button>

                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => handleOpenSchema(product)}
                                            >
                                                <Settings className="w-4 h-4 mr-1.5" />
                                                {t('dataProducts.editSchema')}
                                            </Button>

                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => router.push(`/${locale}/data-products/${product.id}/mappings`)}
                                            >
                                                <Link2 className="w-4 h-4 mr-1.5" />
                                                {t('dataProducts.configMappings')}
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
