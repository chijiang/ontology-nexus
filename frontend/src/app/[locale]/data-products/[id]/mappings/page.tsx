'use client'

import { useState, useEffect, use } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations, useLocale } from 'next-intl'
import {
    ArrowLeft,
    Plus,
    Trash2,
    RefreshCw,
    Link2,
    ChevronDown,
    ChevronRight,
    Server,
    Box,
    ArrowRight,
    Check,
    X,
    Activity,
    ClipboardList,
    History
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
    Tabs,
    TabsContent,
    TabsList,
    TabsTrigger
} from '@/components/ui/tabs'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import { AppLayout } from '@/components/layout'
import {
    dataProductsApi,
    dataMappingsApi,
    graphApi,
    DataProduct,
    EntityMapping,
    PropertyMapping,
    SyncDirection,
    RelationshipMapping,
    SyncLogResponse
} from '@/lib/api'

interface OntologyClass {
    name: string
    label: string
    data_properties: string[]
}

export default function DataMappingsPage({ params }: { params: Promise<{ id: string }> }) {
    const resolvedParams = use(params)
    const productId = parseInt(resolvedParams.id)
    const router = useRouter()
    const t = useTranslations()
    const tCommon = useTranslations('common')
    const tMappings = useTranslations('mappings')
    const tDataProducts = useTranslations('dataProducts')
    const locale = useLocale()

    const [product, setProduct] = useState<DataProduct | null>(null)
    const [entityMappings, setEntityMappings] = useState<EntityMapping[]>([])
    const [relationshipMappings, setRelationshipMappings] = useState<RelationshipMapping[]>([])
    const [syncLogs, setSyncLogs] = useState<SyncLogResponse[]>([])
    const [ontologyClasses, setOntologyClasses] = useState<OntologyClass[]>([])
    const [loading, setLoading] = useState(true)
    const [isSyncing, setIsSyncing] = useState(false)

    // Entity mapping dialog
    const [entityDialogOpen, setEntityDialogOpen] = useState(false)
    const [entityForm, setEntityForm] = useState({
        ontology_class_name: '',
        grpc_message_type: '',
        list_method: '',
        sync_direction: 'pull' as SyncDirection,
    })
    const [creatingEntity, setCreatingEntity] = useState(false)

    // Property mapping state
    const [expandedMapping, setExpandedMapping] = useState<number | null>(null)
    const [propertyMappings, setPropertyMappings] = useState<Record<number, PropertyMapping[]>>({})
    const [loadingProperties, setLoadingProperties] = useState<number | null>(null)

    // Property mapping dialog
    const [propertyDialogOpen, setPropertyDialogOpen] = useState(false)
    const [selectedEntityMapping, setSelectedEntityMapping] = useState<EntityMapping | null>(null)
    const [propertyForm, setPropertyForm] = useState({
        ontology_property: '',
        grpc_field: '',
        transformation: 'None',
    })

    const TRANSFORMATION_OPTIONS = [
        { label: t('mappings.transformNone'), value: 'None' },
        { label: t('mappings.transformParseNum'), value: 'parseNum' },
        { label: t('mappings.transformToString'), value: 'toString' },
        { label: t('mappings.transformToDate'), value: 'toDate' },
    ]
    const [creatingProperty, setCreatingProperty] = useState(false)

    // Relationship mapping dialog
    const [relDialogOpen, setRelDialogOpen] = useState(false)
    const [relForm, setRelForm] = useState({
        source_entity_mapping_id: '',
        target_entity_mapping_id: '',
        ontology_relationship: '',
        source_fk_field: '',
        target_id_field: 'id'
    })
    const [creatingRel, setCreatingRel] = useState(false)

    const loadData = async () => {
        try {
            setLoading(true)

            // Load product info
            const productRes = await dataProductsApi.get(productId)
            setProduct(productRes.data)

            // Load entity mappings
            const mappingsRes = await dataProductsApi.getEntityMappings(productId)
            setEntityMappings(mappingsRes.data.items)

            // Load relationship mappings
            const relRes = await dataMappingsApi.listRelationshipMappings()
            // Filter by mappings in this product
            const mappingIds = mappingsRes.data.items.map(m => m.id)
            setRelationshipMappings(relRes.data.filter(r => mappingIds.includes(r.source_entity_mapping_id)))

            // Load sync logs
            const logsRes = await dataProductsApi.getSyncLogs(productId)
            setSyncLogs(logsRes.data)

            // Load ontology classes
            const tokenValue = localStorage.getItem('auth-storage')
            if (tokenValue) {
                const auth = JSON.parse(tokenValue)
                const schemaRes = await graphApi.getSchema(auth.state.token)
                // 后端返回的 nodes 列表直接就是类定义对象
                const classes = (schemaRes.data.nodes || []).map((n: any) => ({
                    name: n.name,
                    label: n.label || n.name,
                    data_properties: n.dataProperties || [],
                }))
                setOntologyClasses(classes)
            }
        } catch (error) {
            toast.error(tCommon('error'), {
                description: t('mappings.loadFailed'),
            })
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (productId) {
            loadData()
        }
    }, [productId])

    const loadPropertyMappings = async (entityMappingId: number) => {
        try {
            setLoadingProperties(entityMappingId)
            const res = await dataMappingsApi.listPropertyMappings(entityMappingId)
            setPropertyMappings(prev => ({
                ...prev,
                [entityMappingId]: res.data,
            }))
        } catch (error) {
            toast.error(tCommon('error'), {
                description: t('mappings.loadPropertiesFailed'),
            })
        } finally {
            setLoadingProperties(null)
        }
    }

    const handleExpandMapping = (mappingId: number) => {
        if (expandedMapping === mappingId) {
            setExpandedMapping(null)
        } else {
            setExpandedMapping(mappingId)
            if (!propertyMappings[mappingId]) {
                loadPropertyMappings(mappingId)
            }
        }
    }

    const handleCreateEntityMapping = async () => {
        if (!entityForm.ontology_class_name || !entityForm.grpc_message_type) {
            toast.error(tDataProducts('validationFailed'), {
                description: t('mappings.selectClassAndMessage'),
            })
            return
        }

        try {
            setCreatingEntity(true)
            await dataMappingsApi.createEntityMapping({
                data_product_id: productId,
                ...entityForm,
            })
            toast.success(tCommon('success'), {
                description: t('mappings.mappingCreated'),
            })
            setEntityDialogOpen(false)
            setEntityForm({
                ontology_class_name: '',
                grpc_message_type: '',
                list_method: '',
                sync_direction: 'pull',
            })
            loadData()
        } catch (error: any) {
            toast.error(tCommon('error'), {
                description: error.response?.data?.detail || tDataProducts('fillRequired'),
            })
        } finally {
            setCreatingEntity(false)
        }
    }

    const handleDeleteEntityMapping = async (mappingId: number) => {
        if (!confirm(t('mappings.deleteEntityConfirm'))) {
            return
        }

        try {
            await dataMappingsApi.deleteEntityMapping(mappingId)
            toast.success(tCommon('delete'), {
                description: t('mappings.entityMappingDeleted'),
            })
            loadData()
        } catch (error: any) {
            toast.error(tDataProducts('deleteFailed'), {
                description: error.response?.data?.detail || tDataProducts('deleteFailedDesc'),
            })
        }
    }

    const handleOpenPropertyDialog = (mapping: EntityMapping) => {
        setSelectedEntityMapping(mapping)
        setPropertyDialogOpen(true)
    }

    const handleCreatePropertyMapping = async () => {
        if (!selectedEntityMapping || !propertyForm.ontology_property || !propertyForm.grpc_field) {
            toast.error(tDataProducts('validationFailed'), {
                description: tDataProducts('fillRequired'),
            })
            return
        }

        try {
            setCreatingProperty(true)

            let transform_expression = undefined
            if (propertyForm.transformation !== 'None') {
                transform_expression = `${propertyForm.transformation}(value)`
            }

            await dataMappingsApi.createPropertyMapping(selectedEntityMapping.id, {
                ontology_property: propertyForm.ontology_property.split(':')[0],
                grpc_field: propertyForm.grpc_field,
                transform_expression: transform_expression
            })
            toast.success(tCommon('success'), {
                description: t('mappings.propertyMappingCreated'),
            })
            setPropertyDialogOpen(false)
            setPropertyForm({ ontology_property: '', grpc_field: '', transformation: 'None' })
            loadPropertyMappings(selectedEntityMapping.id)
            loadData() // Refresh count
        } catch (error: any) {
            toast.error(tCommon('error'), {
                description: error.response?.data?.detail || tDataProducts('fillRequired'),
            })
        } finally {
            setCreatingProperty(false)
        }
    }

    const handleDeletePropertyMapping = async (propId: number, entityMappingId: number) => {
        try {
            await dataMappingsApi.deletePropertyMapping(propId)
            toast.success(tCommon('delete'), {
                description: t('mappings.propertyMappingDeleted'),
            })
            loadPropertyMappings(entityMappingId)
            loadData()
        } catch (error: any) {
            toast.error(tDataProducts('deleteFailed'), {
                description: error.response?.data?.detail || tDataProducts('deleteFailedDesc'),
            })
        }
    }

    const handleCreateRelationshipMapping = async () => {
        if (!relForm.source_entity_mapping_id || !relForm.target_entity_mapping_id || !relForm.ontology_relationship || !relForm.source_fk_field) {
            toast.error(tDataProducts('validationFailed'), {
                description: tDataProducts('fillRequired'),
            })
            return
        }

        try {
            setCreatingRel(true)
            await dataMappingsApi.createRelationshipMapping({
                source_entity_mapping_id: parseInt(relForm.source_entity_mapping_id),
                target_entity_mapping_id: parseInt(relForm.target_entity_mapping_id),
                ontology_relationship: relForm.ontology_relationship,
                source_fk_field: relForm.source_fk_field,
                target_id_field: relForm.target_id_field
            })
            toast.success(tCommon('success'), {
                description: t('mappings.relationshipMappingCreated'),
            })
            setRelDialogOpen(false)
            setRelForm({
                source_entity_mapping_id: '',
                target_entity_mapping_id: '',
                ontology_relationship: '',
                source_fk_field: '',
                target_id_field: 'id'
            })
            loadData()
        } catch (error: any) {
            toast.error(tCommon('error'), {
                description: error.response?.data?.detail || tDataProducts('fillRequired'),
            })
        } finally {
            setCreatingRel(false)
        }
    }

    const handleDeleteRelationshipMapping = async (id: number) => {
        if (!confirm(t('mappings.deleteRelationshipConfirm'))) return

        try {
            await dataMappingsApi.deleteRelationshipMapping(id)
            toast.success(tCommon('delete'))
            loadData()
        } catch (error: any) {
            toast.error(tDataProducts('deleteFailed'))
        }
    }

    const handleTriggerSync = async () => {
        try {
            setIsSyncing(true)
            toast.info(t('mappings.syncStarted'), {
                description: t('mappings.syncingFromDataSource'),
            })
            const res = await dataProductsApi.triggerSync(productId)
            toast.success(t('mappings.syncCompleted'), {
                description: t('mappings.syncResults', {
                    processed: res.data.records_processed,
                    created: res.data.records_created,
                    updated: res.data.records_updated
                }),
            })
            loadData()
        } catch (error: any) {
            toast.error(tMappings('syncFailed'), {
                description: error.response?.data?.detail || t('mappings.syncError')
            })
        } finally {
            setIsSyncing(false)
        }
    }


    const getSelectedClass = () => {
        return ontologyClasses.find(c => c.name === entityForm.ontology_class_name)
    }

    const getSelectedMappingClass = () => {
        if (!selectedEntityMapping) return null
        return ontologyClasses.find(c => c.name === selectedEntityMapping.ontology_class_name)
    }

    if (loading) {
        return (
            <AppLayout>
                <div className="flex items-center justify-center min-h-[400px]">
                    <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
                </div>
            </AppLayout>
        )
    }

    return (
        <AppLayout>
            {/* Header */}
            <div className="flex items-center gap-4 mb-8">
                <Button variant="ghost" size="icon" onClick={() => router.push(`/${locale}/data-products`)}>
                    <ArrowLeft className="w-5 h-5" />
                </Button>
                <div className="flex-1">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-primary/10 rounded-lg">
                            <Server className="w-5 h-5 text-primary" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold">{product?.name}</h1>
                            <p className="text-muted-foreground text-sm">
                                {product?.grpc_host}:{product?.grpc_port} / {product?.service_name}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <Button
                        variant="default"
                        onClick={handleTriggerSync}
                        disabled={isSyncing}
                        className="bg-green-600 hover:bg-green-700 text-white"
                    >
                        {isSyncing ? (
                            <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                        ) : (
                            <Activity className="w-4 h-4 mr-2" />
                        )}
                        {isSyncing ? t('mappings.syncing') : tMappings('syncNow')}
                    </Button>
                </div>
            </div>

            <Tabs defaultValue="entities" className="space-y-6">
                <TabsList className="grid w-full max-w-md grid-cols-3">
                    <TabsTrigger value="entities" className="flex items-center gap-2">
                        <Box className="w-4 h-4" />
                        {tMappings('entityMappings')}
                    </TabsTrigger>
                    <TabsTrigger value="relationships" className="flex items-center gap-2">
                        <Link2 className="w-4 h-4" />
                        {tMappings('relationshipMappings')}
                    </TabsTrigger>
                    <TabsTrigger value="history" className="flex items-center gap-2">
                        <History className="w-4 h-4" />
                        {tMappings('syncLogs')}
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="entities" className="space-y-4">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-lg font-semibold">{tMappings('entityTypeMappings')}</h2>
                        <Dialog open={entityDialogOpen} onOpenChange={setEntityDialogOpen}>
                            <DialogTrigger asChild>
                                <Button size="sm">
                                    <Plus className="w-4 h-4 mr-2" />
                                    {tMappings('addEntityMapping')}
                                </Button>
                            </DialogTrigger>
                            <DialogContent className="sm:max-w-[500px]">
                                <DialogHeader>
                                    <DialogTitle>{tMappings('addEntityMapping')}</DialogTitle>
                                    <DialogDescription>
                                        {tMappings('addEntityMappingDesc')}
                                    </DialogDescription>
                                </DialogHeader>

                                <div className="grid gap-4 py-4">
                                    <div className="grid gap-2">
                                        <Label>{tMappings('ontologyClass')} *</Label>
                                        <Select
                                            value={entityForm.ontology_class_name}
                                            onValueChange={(v: string) => setEntityForm({ ...entityForm, ontology_class_name: v })}
                                        >
                                            <SelectTrigger>
                                                <SelectValue placeholder={tMappings('selectOntologyClass')} />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {ontologyClasses.map((cls) => (
                                                    <SelectItem key={cls.name} value={cls.name}>
                                                        {cls.label || cls.name}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    <div className="grid gap-2">
                                        <Label>{tMappings('grpcMessage')} *</Label>
                                        <Input
                                            placeholder={tMappings('grpcMessagePlaceholder')}
                                            value={entityForm.grpc_message_type}
                                            onChange={(e) => setEntityForm({ ...entityForm, grpc_message_type: e.target.value })}
                                        />
                                    </div>

                                    <div className="grid gap-2">
                                        <Label>{tMappings('listMethod')}</Label>
                                        <Input
                                            placeholder={tMappings('listMethodPlaceholder')}
                                            value={entityForm.list_method}
                                            onChange={(e) => setEntityForm({ ...entityForm, list_method: e.target.value })}
                                        />
                                    </div>

                                    <div className="grid gap-2">
                                        <Label>{tMappings('syncDirection')}</Label>
                                        <Select
                                            value={entityForm.sync_direction}
                                            onValueChange={(v: SyncDirection) => setEntityForm({ ...entityForm, sync_direction: v })}
                                        >
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="pull">{tMappings('pullFromDataSource')}</SelectItem>
                                                <SelectItem value="push">{tMappings('pushToDataSource')}</SelectItem>
                                                <SelectItem value="bidirectional">{tMappings('bidirectionalSync')}</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>

                                <DialogFooter>
                                    <Button variant="outline" onClick={() => setEntityDialogOpen(false)}>
                                        {tCommon('cancel')}
                                    </Button>
                                    <Button onClick={handleCreateEntityMapping} disabled={creatingEntity}>
                                        {creatingEntity ? t('mappings.creating') : tCommon('create')}
                                    </Button>
                                </DialogFooter>
                            </DialogContent>
                        </Dialog>
                    </div>

                    {entityMappings.length === 0 ? (
                        <Card className="border-dashed">
                            <CardContent className="flex flex-col items-center justify-center py-12">
                                <Link2 className="w-12 h-12 text-muted-foreground mb-4" />
                                <h3 className="text-lg font-medium mb-2">{tMappings('noMappings')}</h3>
                                <p className="text-muted-foreground text-sm mb-4">
                                    {tMappings('noMappingsDesc')}
                                </p>
                                <Button onClick={() => setEntityDialogOpen(true)}>
                                    <Plus className="w-4 h-4 mr-2" />
                                    {tMappings('addEntityMapping')}
                                </Button>
                            </CardContent>
                        </Card>
                    ) : (
                        <div className="space-y-4">
                            {entityMappings.map((mapping) => (
                                <Card key={mapping.id} className="overflow-hidden">
                                    <CardHeader
                                        className="pb-3 cursor-pointer hover:bg-muted/30 transition-colors"
                                        onClick={() => handleExpandMapping(mapping.id)}
                                    >
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-4">
                                                {expandedMapping === mapping.id ? (
                                                    <ChevronDown className="w-5 h-5 text-muted-foreground" />
                                                ) : (
                                                    <ChevronRight className="w-5 h-5 text-muted-foreground" />
                                                )}

                                                <div className="flex items-center gap-3">
                                                    <div className="p-1.5 bg-blue-500/10 rounded">
                                                        <Box className="w-4 h-4 text-blue-500" />
                                                    </div>
                                                    <span className="font-medium text-lg">{mapping.ontology_class_name}</span>
                                                </div>

                                                <ArrowRight className="w-4 h-4 text-muted-foreground" />

                                                <div className="flex items-center gap-3">
                                                    <div className="p-1.5 bg-green-500/10 rounded">
                                                        <Server className="w-4 h-4 text-green-500" />
                                                    </div>
                                                    <span className="font-medium text-lg">{mapping.grpc_message_type}</span>
                                                </div>
                                            </div>

                                            <div className="flex items-center gap-4" onClick={(e) => e.stopPropagation()}>
                                                <div className="flex flex-col items-end mr-4">
                                                    <span className="text-sm font-semibold">{mapping.property_mapping_count}</span>
                                                    <span className="text-[10px] uppercase text-muted-foreground">{tMappings('propertyMappings')}</span>
                                                </div>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="text-muted-foreground hover:text-red-500"
                                                    onClick={() => handleDeleteEntityMapping(mapping.id)}
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </Button>
                                            </div>
                                        </div>
                                    </CardHeader>

                                    {expandedMapping === mapping.id && (
                                        <CardContent className="pt-0 bg-muted/5 animate-in slide-in-from-top-1 duration-200">
                                            <div className="border-t pt-4">
                                                <div className="flex items-center justify-between mb-4">
                                                    <h4 className="text-sm font-semibold flex items-center gap-2">
                                                        <Activity className="w-3.5 h-3.5" />
                                                        {tMappings('fieldMappingRules')}
                                                    </h4>
                                                    <Button
                                                        variant="outline"
                                                        size="sm"
                                                        onClick={() => handleOpenPropertyDialog(mapping)}
                                                        className="h-8"
                                                    >
                                                        <Plus className="w-3.5 h-3.5 mr-1" />
                                                        {tMappings('addProperty')}
                                                    </Button>
                                                </div>

                                                {loadingProperties === mapping.id ? (
                                                    <div className="flex items-center justify-center py-6">
                                                        <RefreshCw className="w-5 h-5 animate-spin text-primary/40" />
                                                    </div>
                                                ) : (propertyMappings[mapping.id]?.length || 0) === 0 ? (
                                                    <div className="text-center py-8 bg-muted/20 rounded-xl border border-dashed">
                                                        <p className="text-sm text-muted-foreground">
                                                            {tMappings('noPropertyMappingsDesc')}
                                                        </p>
                                                    </div>
                                                ) : (
                                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pb-4">
                                                        {propertyMappings[mapping.id]?.map((prop) => (
                                                            <div
                                                                key={prop.id}
                                                                className="flex items-center justify-between p-3 bg-white dark:bg-zinc-900 border rounded-xl shadow-sm group hover:border-primary/50 transition-colors"
                                                            >
                                                                <div className="flex items-center gap-3">
                                                                    <div className="flex flex-col">
                                                                        <span className="text-xs text-muted-foreground uppercase tracking-widest font-bold">{tMappings('graphProperty')}</span>
                                                                        <span className="text-sm font-mono font-bold">{prop.ontology_property.split(':')[0]}</span>
                                                                    </div>
                                                                    <ArrowRight className="w-3.5 h-3.5 text-muted-foreground mx-1" />
                                                                    <div className="flex flex-col">
                                                                        <span className="text-xs text-muted-foreground uppercase tracking-widest font-bold">{tMappings('dataSourceField')}</span>
                                                                        <div className="flex items-center gap-1.5">
                                                                            <span className="text-sm font-mono font-bold">{prop.grpc_field}</span>
                                                                            {prop.transform_expression && (
                                                                                <span className="text-[10px] bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded font-mono">
                                                                                    {prop.transform_expression}
                                                                                </span>
                                                                            )}
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                                <Button
                                                                    variant="ghost"
                                                                    size="icon"
                                                                    className="h-8 w-8 text-muted-foreground hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                                                                    onClick={() => handleDeletePropertyMapping(prop.id, mapping.id)}
                                                                >
                                                                    <X className="w-4 h-4" />
                                                                </Button>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </CardContent>
                                    )}
                                </Card>
                            ))}
                        </div>
                    )}
                </TabsContent>

                <TabsContent value="relationships" className="space-y-4">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-lg font-semibold">{tMappings('entityRelationshipMappings')}</h2>
                        <Dialog open={relDialogOpen} onOpenChange={setRelDialogOpen}>
                            <DialogTrigger asChild>
                                <Button size="sm">
                                    <Plus className="w-4 h-4 mr-2" />
                                    {tMappings('addRelationshipMapping')}
                                </Button>
                            </DialogTrigger>
                            <DialogContent className="sm:max-w-[500px]">
                                <DialogHeader>
                                    <DialogTitle>{tMappings('addRelationshipMapping')}</DialogTitle>
                                    <DialogDescription>
                                        {tMappings('addRelationshipMappingDesc')}
                                    </DialogDescription>
                                </DialogHeader>

                                <div className="grid gap-4 py-4">
                                    <div className="grid gap-2">
                                        <Label>{tMappings('sourceEntityMapping')} *</Label>
                                        <Select
                                            value={relForm.source_entity_mapping_id}
                                            onValueChange={(v) => setRelForm({ ...relForm, source_entity_mapping_id: v })}
                                        >
                                            <SelectTrigger>
                                                <SelectValue placeholder={tMappings('selectSourceMapping')} />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {entityMappings.map((m) => (
                                                    <SelectItem key={m.id} value={m.id.toString()}>
                                                        {m.ontology_class_name} ({m.grpc_message_type})
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    <div className="grid gap-2">
                                        <Label>{tMappings('targetEntityMapping')} *</Label>
                                        <Select
                                            value={relForm.target_entity_mapping_id}
                                            onValueChange={(v) => setRelForm({ ...relForm, target_entity_mapping_id: v })}
                                        >
                                            <SelectTrigger>
                                                <SelectValue placeholder={tMappings('selectTargetMapping')} />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {entityMappings.map((m) => (
                                                    <SelectItem key={m.id} value={m.id.toString()}>
                                                        {m.ontology_class_name} ({m.grpc_message_type})
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    <div className="grid gap-2">
                                        <Label>{tMappings('ontologyRelationship')} *</Label>
                                        <Input
                                            placeholder={tMappings('relationshipPlaceholder')}
                                            value={relForm.ontology_relationship}
                                            onChange={(e) => setRelForm({ ...relForm, ontology_relationship: e.target.value })}
                                        />
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="grid gap-2">
                                            <Label>{tMappings('sourceForeignKey')} *</Label>
                                            <Input
                                                placeholder={tMappings('sourceForeignKeyPlaceholder')}
                                                value={relForm.source_fk_field}
                                                onChange={(e) => setRelForm({ ...relForm, source_fk_field: e.target.value })}
                                            />
                                        </div>
                                        <div className="grid gap-2">
                                            <Label>{tMappings('targetIdField')}</Label>
                                            <Input
                                                placeholder={tMappings('targetIdFieldPlaceholder')}
                                                value={relForm.target_id_field}
                                                onChange={(e) => setRelForm({ ...relForm, target_id_field: e.target.value })}
                                            />
                                        </div>
                                    </div>
                                </div>

                                <DialogFooter>
                                    <Button variant="outline" onClick={() => setRelDialogOpen(false)}>
                                        {tCommon('cancel')}
                                    </Button>
                                    <Button onClick={handleCreateRelationshipMapping} disabled={creatingRel}>
                                        {creatingRel ? t('mappings.creating') : tCommon('create')}
                                    </Button>
                                </DialogFooter>
                            </DialogContent>
                        </Dialog>
                    </div>

                    {relationshipMappings.length === 0 ? (
                        <Card className="border-dashed">
                            <CardContent className="flex flex-col items-center justify-center py-12">
                                <Link2 className="w-12 h-12 text-muted-foreground mb-4" />
                                <h3 className="text-lg font-medium mb-2">{tMappings('noRelationshipMappings')}</h3>
                                <p className="text-muted-foreground text-sm mb-4">
                                    {tMappings('noRelationshipMappingsDesc')}
                                </p>
                                <Button onClick={() => setRelDialogOpen(true)}>
                                    <Plus className="w-4 h-4 mr-2" />
                                    {tMappings('addRelationshipMapping')}
                                </Button>
                            </CardContent>
                        </Card>
                    ) : (
                        <div className="grid grid-cols-1 gap-4">
                            {relationshipMappings.map((rel) => (
                                <Card key={rel.id} className="group relative overflow-hidden border-primary/10">
                                    <CardContent className="p-6">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-6">
                                                <div className="flex flex-col">
                                                    <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1">{tMappings('sourceEntityWithFk')}</span>
                                                    <div className="flex items-center gap-2">
                                                        <Box className="w-4 h-4 text-blue-500" />
                                                        <span className="font-bold">{rel.source_ontology_class || t('mappings.notLoaded')}</span>
                                                    </div>
                                                </div>

                                                <div className="flex flex-col items-center px-4">
                                                    <span className="text-[11px] font-mono bg-primary/10 text-primary px-2 py-0.5 rounded-full mb-1">
                                                        {rel.ontology_relationship}
                                                    </span>
                                                    <div className="flex items-center gap-1">
                                                        <div className="h-px w-8 bg-muted-foreground/30"></div>
                                                        <ChevronRight className="w-3 h-3 text-muted-foreground/50" />
                                                        <div className="h-px w-8 bg-muted-foreground/30"></div>
                                                    </div>
                                                </div>

                                                <div className="flex flex-col">
                                                    <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1">{tMappings('targetEntity')}</span>
                                                    <div className="flex items-center gap-2">
                                                        <Box className="w-4 h-4 text-green-500" />
                                                        <span className="font-bold">{rel.target_ontology_class || t('mappings.notLoaded')}</span>
                                                    </div>
                                                </div>

                                                <div className="ml-8 px-4 border-l flex flex-col">
                                                    <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1">{tMappings('matchingLogic')}</span>
                                                    <span className="text-sm">
                                                        <span className="font-mono bg-muted px-1.5 py-0.5 rounded">{rel.source_fk_field}</span>
                                                        <span className="mx-2 text-muted-foreground">→</span>
                                                        <span className="font-mono bg-muted px-1.5 py-0.5 rounded">{rel.target_id_field}</span>
                                                    </span>
                                                </div>
                                            </div>

                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="text-muted-foreground hover:text-red-500 hover:bg-red-50"
                                                onClick={() => handleDeleteRelationshipMapping(rel.id)}
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </Button>
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    )}
                </TabsContent>

                <TabsContent value="history" className="space-y-4">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-lg font-semibold">{tMappings('syncHistory')}</h2>
                        <Button variant="outline" size="sm" onClick={loadData}>
                            <RefreshCw className="w-4 h-4 mr-2" />
                            {tMappings('refreshLogs')}
                        </Button>
                    </div>

                    <div className="border rounded-xl overflow-hidden bg-white dark:bg-zinc-950">
                        {syncLogs.length === 0 ? (
                            <div className="p-12 text-center">
                                <ClipboardList className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                                <p className="text-muted-foreground">{tMappings('noSyncLogsDesc')}</p>
                            </div>
                        ) : (
                            <div className="divide-y">
                                <div className="grid grid-cols-6 gap-4 p-4 bg-muted/30 font-bold text-xs uppercase tracking-wider">
                                    <div className="col-span-1">{tMappings('status')}</div>
                                    <div className="col-span-1">{tMappings('typeDirection')}</div>
                                    <div className="col-span-1 text-center">{tMappings('processedRecords')}</div>
                                    <div className="col-span-1 text-center">{tMappings('createdUpdated')}</div>
                                    <div className="col-span-1">{tMappings('startTime')}</div>
                                    <div className="col-span-1">{tMappings('durationNotes')}</div>
                                </div>
                                {syncLogs.map((log) => (
                                    <div key={log.id} className="grid grid-cols-6 gap-4 p-4 text-sm items-center hover:bg-muted/10 transition-colors">
                                        <div className="col-span-1">
                                            {log.status === 'completed' ? (
                                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
                                                    <Check className="w-3 h-3 mr-1" /> {tMappings('completed')}
                                                </span>
                                            ) : log.status === 'started' ? (
                                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                                                    <RefreshCw className="w-3 h-3 mr-1 animate-spin" /> {tMappings('inProgress')}
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
                                                    <X className="w-3 h-3 mr-1" /> {tMappings('failed')}
                                                </span>
                                            )}
                                        </div>
                                        <div className="col-span-1 flex flex-col">
                                            <span className="capitalize">{log.sync_type}</span>
                                            <span className="text-[10px] text-muted-foreground uppercase">{log.direction}</span>
                                        </div>
                                        <div className="col-span-1 text-center font-mono font-bold">
                                            {log.records_processed}
                                        </div>
                                        <div className="col-span-1 text-center">
                                            <span className="text-green-600 font-bold">+{log.records_created}</span>
                                            <span className="mx-1 text-muted-foreground">/</span>
                                            <span className="text-blue-600 font-bold">~{log.records_updated}</span>
                                        </div>
                                        <div className="col-span-1 text-xs text-muted-foreground">
                                            {new Date(log.started_at).toLocaleString()}
                                        </div>
                                        <div className="col-span-1 text-xs truncate" title={log.error_message || ''}>
                                            {log.completed_at ? (
                                                <span className="text-muted-foreground">
                                                    {Math.round((new Date(log.completed_at).getTime() - new Date(log.started_at).getTime()) / 1000)}s
                                                </span>
                                            ) : '-'}
                                            {log.error_message && (
                                                <div className="text-red-500 font-medium text-[10px] mt-1 truncate">
                                                    {log.error_message}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </TabsContent>
            </Tabs>

            {/* Property Mapping Dialog */}
            <Dialog open={propertyDialogOpen} onOpenChange={setPropertyDialogOpen}>
                <DialogContent className="sm:max-w-[400px]">
                    <DialogHeader>
                        <DialogTitle>{tMappings('addPropertyMapping')}</DialogTitle>
                        <DialogDescription>
                            {tMappings('addPropertyMappingDesc')}
                        </DialogDescription>
                    </DialogHeader>

                    <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                            <Label>{tMappings('ontologyProperty')}</Label>
                            {getSelectedMappingClass()?.data_properties?.length ? (
                                <Select
                                    value={propertyForm.ontology_property}
                                    onValueChange={(v: string) => setPropertyForm({ ...propertyForm, ontology_property: v })}
                                >
                                    <SelectTrigger>
                                        <SelectValue placeholder={tMappings('selectProperty')} />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {getSelectedMappingClass()?.data_properties.map((prop: string) => {
                                            const [name, type] = prop.split(':')
                                            return (
                                                <SelectItem key={prop} value={name}>
                                                    <div className="flex justify-between w-full items-center">
                                                        <span>{name}</span>
                                                        <span className="text-[10px] text-muted-foreground ml-2 px-1 bg-muted rounded">
                                                            {type || 'string'}
                                                        </span>
                                                    </div>
                                                </SelectItem>
                                            )
                                        })}
                                    </SelectContent>
                                </Select>
                            ) : (
                                <Input
                                    placeholder={tMappings('enterPropertyName')}
                                    value={propertyForm.ontology_property}
                                    onChange={(e) => setPropertyForm({ ...propertyForm, ontology_property: e.target.value })}
                                />
                            )}
                        </div>

                        <div className="grid gap-2">
                            <Label>{tMappings('grpcField')}</Label>
                            <Input
                                placeholder={tMappings('enterFieldName')}
                                value={propertyForm.grpc_field}
                                onChange={(e) => setPropertyForm({ ...propertyForm, grpc_field: e.target.value })}
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label>{tMappings('dataTransform')}</Label>
                            <Select
                                value={propertyForm.transformation}
                                onValueChange={(v: string) => setPropertyForm({ ...propertyForm, transformation: v })}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder={tMappings('selectTransformFunction')} />
                                </SelectTrigger>
                                <SelectContent>
                                    {TRANSFORMATION_OPTIONS.map((opt) => (
                                        <SelectItem key={opt.value} value={opt.value}>
                                            {opt.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setPropertyDialogOpen(false)}>
                            {tCommon('cancel')}
                        </Button>
                        <Button onClick={handleCreatePropertyMapping} disabled={creatingProperty}>
                            {creatingProperty ? t('mappings.creating') : tCommon('create')}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </AppLayout >
    )
}

