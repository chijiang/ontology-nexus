'use client'

import { useEffect, useState } from 'react'
import {
    dataProductsApi,
    dataMappingsApi,
    DataProduct,
    EntityMapping,
    PropertyMapping,
    RelationshipMapping,
    GrpcServiceSchema,
    SyncDirection
} from '@/lib/api'
import {
    X,
    Database,
    ArrowRight,
    Link2,
    Plus,
    Trash2,
    Save,
    Loader2,
    ExternalLink,
    Settings2,
    CheckCircle2,
    AlertCircle
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue
} from '@/components/ui/select'
import { toast } from 'sonner'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { useTranslations } from 'next-intl'

import { Selection, OntologyNode } from '@/types/ontology'

interface BindingDetailPanelProps {
    selection: Selection | null
    onUpdate?: () => void
    onClose: () => void
}

export function BindingDetailPanel({ selection, onUpdate, onClose }: BindingDetailPanelProps) {
    const t = useTranslations()
    const [loading, setLoading] = useState(false)
    const [products, setProducts] = useState<DataProduct[]>([])

    // Entity specific state
    const [entityMappings, setEntityMappings] = useState<EntityMapping[]>([])
    const [isAddingMapping, setIsAddingMapping] = useState(false)
    const [newMapping, setNewMapping] = useState({
        data_product_id: '',
        grpc_message_type: '',
        list_method: '',
        id_field_mapping: 'id',
        name_field_mapping: 'name'
    })
    const [selectedProductSchema, setSelectedProductSchema] = useState<GrpcServiceSchema | null>(null)
    const [fetchingSchema, setFetchingSchema] = useState(false)

    // Property mapping state
    const [activeMappingId, setActiveMappingId] = useState<number | null>(null)
    const [propertyMappings, setPropertyMappings] = useState<PropertyMapping[]>([])
    const [isAddingProp, setIsAddingProp] = useState(false)
    const [newProp, setNewProp] = useState({
        ontology_property: '',
        grpc_field: '',
        transformation: 'None'
    })

    const TRANSFORMATION_OPTIONS = [
        { label: `${t('mappings.transformNone')} (None)`, value: 'None' },
        { label: `${t('mappings.transformParseNum')} (parseNum)`, value: 'parseNum' },
        { label: `${t('mappings.transformToString')} (toString)`, value: 'toString' },
        { label: `${t('mappings.transformToDate')} (toDate)`, value: 'toDate' },
    ]
    const [isCustomProp, setIsCustomProp] = useState(false)

    // Relationship specific state
    const [relMappings, setRelMappings] = useState<RelationshipMapping[]>([])
    const [isAddingRel, setIsAddingRel] = useState(false)
    const [sourceMappings, setSourceMappings] = useState<EntityMapping[]>([])
    const [targetMappings, setTargetMappings] = useState<EntityMapping[]>([])
    const [newRel, setNewRel] = useState({
        source_entity_mapping_id: '',
        target_entity_mapping_id: '',
        source_fk_field: '',
        target_id_field: ''
    })

    const node = selection?.type === 'node' ? selection.data : null
    const edge = selection?.type === 'edge' ? selection.data : null

    useEffect(() => {
        loadBaseData()
    }, [])

    useEffect(() => {
        if (selection) {
            loadMappings()
            setIsAddingMapping(false)
            setIsAddingRel(false)
            setSelectedProductSchema(null)
        }
    }, [selection])

    // Auto-select Message and Method if names match
    useEffect(() => {
        if (selectedProductSchema && node && isAddingMapping) {
            const lowerNodeName = node.name.toLowerCase()

            // Try to find matching message type
            const matchedMsg = selectedProductSchema.message_types.find(
                m => m.name.toLowerCase() === lowerNodeName ||
                    m.name.toLowerCase().endsWith(lowerNodeName)
            )

            if (matchedMsg) {
                // Try to find matching list method (e.g. ListSuppliers, GetSuppliers)
                const matchedMethod = selectedProductSchema.methods.find(
                    m => m.name.toLowerCase().includes(`list${lowerNodeName}`) ||
                        m.name.toLowerCase().includes(`get${lowerNodeName}`)
                )

                setNewMapping(prev => ({
                    ...prev,
                    grpc_message_type: matchedMsg.name,
                    list_method: matchedMethod ? matchedMethod.name : prev.list_method
                }))

                toast.success(t('components.binding.autoMatched'), {
                    description: `${t('components.binding.detectedType')}: ${matchedMsg.name}`,
                    duration: 2000
                })
            }
        }
    }, [selectedProductSchema, node, isAddingMapping])

    const loadBaseData = async () => {
        try {
            const res = await dataProductsApi.list(true)
            setProducts(res.data.items)
        } catch (err) {
            console.error('Failed to load products:', err)
        }
    }

    const loadMappings = async () => {
        if (!selection) return
        setLoading(true)
        try {
            if (node) {
                const res = await dataMappingsApi.listEntityMappings(undefined, node.name)
                setEntityMappings(res.data)
            } else if (edge) {
                // Find relationship mappings by name
                const res = await dataMappingsApi.listRelationshipMappings()
                setRelMappings(res.data.filter(r => r.ontology_relationship === edge.relationship_type))

                // Also load source and target entity mappings to enable binding
                const sRes = await dataMappingsApi.listEntityMappings(undefined, edge.source)
                const tRes = await dataMappingsApi.listEntityMappings(undefined, edge.target)
                setSourceMappings(sRes.data)
                setTargetMappings(tRes.data)
            }
        } catch (err) {
            console.error('Failed to load mappings:', err)
        } finally {
            setLoading(false)
        }
    }

    // Node/Entity Mapping Logic
    const handleProductSelect = async (productId: string) => {
        setNewMapping({ ...newMapping, data_product_id: productId, grpc_message_type: '', list_method: '' })
        setSelectedProductSchema(null)
        setFetchingSchema(true)
        try {
            const res = await dataProductsApi.getSchema(parseInt(productId))
            setSelectedProductSchema(res.data)
        } catch (err) {
            toast.error(t('components.binding.fetchSchemaFailed'), { description: t('components.binding.cannotConnect') })
        } finally {
            setFetchingSchema(false)
        }
    }

    const handleCreateEntityMapping = async () => {
        if (!node || !newMapping.data_product_id || !newMapping.grpc_message_type) return

        try {
            await dataMappingsApi.createEntityMapping({
                data_product_id: parseInt(newMapping.data_product_id),
                ontology_class_name: node.name,
                grpc_message_type: newMapping.grpc_message_type,
                list_method: newMapping.list_method || undefined,
                id_field_mapping: newMapping.id_field_mapping,
                name_field_mapping: newMapping.name_field_mapping
            })
            toast.success(t('components.binding.bindSuccess'))
            setIsAddingMapping(false)
            loadMappings()
            onUpdate?.()
        } catch (err: any) {
            toast.error(t('components.binding.bindFailed'), { description: err.response?.data?.detail || t('components.binding.unknownError') })
        }
    }

    const handleDeleteEntityMapping = async (id: number) => {
        if (!confirm(t('components.binding.confirmUnbind'))) return
        try {
            await dataMappingsApi.deleteEntityMapping(id)
            toast.success(t('components.binding.unbindSuccess'))
            if (activeMappingId === id) setActiveMappingId(null)
            loadMappings()
            onUpdate?.()
        } catch (err) {
            toast.error(t('components.binding.unbindFailed'))
        }
    }

    // Property Mapping Logic
    const handleLoadPropertyMappings = async (mappingId: number) => {
        setActiveMappingId(mappingId)
        setIsAddingProp(false)
        try {
            const res = await dataMappingsApi.listPropertyMappings(mappingId)
            setPropertyMappings(res.data)

            // Also fetch schema to get available gRPC fields if not already loaded
            const mapping = entityMappings.find(m => m.id === mappingId)
            if (mapping && (!selectedProductSchema || selectedProductSchema.service_name !== products.find(p => p.id === mapping.data_product_id)?.service_name)) {
                const sRes = await dataProductsApi.getSchema(mapping.data_product_id)
                setSelectedProductSchema(sRes.data)
            }
        } catch (err) {
            console.error('Failed to load property mappings:', err)
        }
    }

    const handleCreatePropertyMapping = async () => {
        if (!activeMappingId || !newProp.ontology_property || !newProp.grpc_field) return
        try {
            let transform_expression = undefined
            if (newProp.transformation !== 'None') {
                transform_expression = `${newProp.transformation}(value)`
            }

            await dataMappingsApi.createPropertyMapping(activeMappingId, {
                ontology_property: newProp.ontology_property.split(':')[0],
                grpc_field: newProp.grpc_field,
                transform_expression: transform_expression
            })
            toast.success(t('components.binding.propertyMappingAdded'))
            setIsAddingProp(false)
            setNewProp({ ontology_property: '', grpc_field: '', transformation: 'None' })
            handleLoadPropertyMappings(activeMappingId)
        } catch (err) {
            toast.error(t('components.binding.addPropertyFailed'))
        }
    }

    const handleDeletePropertyMapping = async (id: number) => {
        try {
            await dataMappingsApi.deletePropertyMapping(id)
            toast.success(t('components.binding.propertyMappingDeleted'))
            if (activeMappingId) handleLoadPropertyMappings(activeMappingId)
        } catch (err) {
            toast.error(t('components.binding.deleteFailed'))
        }
    }

    // Relationship Mapping Logic
    const [sourceSchema, setSourceSchema] = useState<GrpcServiceSchema | null>(null)
    const [targetSchema, setTargetSchema] = useState<GrpcServiceSchema | null>(null)

    // Fetch schema when source/target mapping changes
    useEffect(() => {
        if (newRel.source_entity_mapping_id) {
            const mapping = sourceMappings.find(m => m.id.toString() === newRel.source_entity_mapping_id.toString())
            if (mapping) {
                // If same as current product, reuse schema, otherwise fetch
                if (products.find(p => p.id === mapping.data_product_id)?.id === selectedProductSchema?.service_name) {
                    // logic is tricky here because we don't have product id in schema. 
                    // simpliest is just fetch. caching can come later.
                }
                dataProductsApi.getSchema(mapping.data_product_id).then(res => setSourceSchema(res.data)).catch(console.error)
            }
        } else {
            setSourceSchema(null)
        }
    }, [newRel.source_entity_mapping_id, sourceMappings, products, selectedProductSchema])

    useEffect(() => {
        if (newRel.target_entity_mapping_id) {
            const mapping = targetMappings.find(m => m.id.toString() === newRel.target_entity_mapping_id.toString())
            if (mapping) {
                dataProductsApi.getSchema(mapping.data_product_id).then(res => setTargetSchema(res.data)).catch(console.error)
            }
        } else {
            setTargetSchema(null)
        }
    }, [newRel.target_entity_mapping_id, targetMappings])

    const handleCreateRelMapping = async () => {
        if (!edge || !newRel.source_entity_mapping_id || !newRel.target_entity_mapping_id || !newRel.source_fk_field) return

        try {
            await dataMappingsApi.createRelationshipMapping({
                source_entity_mapping_id: parseInt(newRel.source_entity_mapping_id),
                target_entity_mapping_id: parseInt(newRel.target_entity_mapping_id),
                ontology_relationship: edge.relationship_type,
                source_fk_field: newRel.source_fk_field,
                target_id_field: newRel.target_id_field || 'id' // Added target_id_field
            })
            toast.success(t('components.binding.relationshipBindSuccess'))
            setIsAddingRel(false)
            setNewRel({ source_entity_mapping_id: '', target_entity_mapping_id: '', source_fk_field: '', target_id_field: '' }) // Reset newRel including target_id_field
            loadMappings()
            onUpdate?.()
        } catch (err: any) {
            toast.error(t('components.binding.bindFailed'), { description: err.response?.data?.detail || t('components.binding.checkConfig') })
        }
    }

    const handleDeleteRelMapping = async (id: number) => {
        if (!confirm(t('components.binding.confirmUnbindRelationship'))) return
        try {
            await dataMappingsApi.deleteRelationshipMapping(id)
            toast.success(t('components.binding.relationshipUnbindSuccess'))
            loadMappings()
            onUpdate?.()
        } catch (err) {
            toast.error(t('components.binding.unbindFailed'))
        }
    }

    if (!selection) return null

    return (
        <div className="bg-white rounded-lg border border-slate-200 h-full flex flex-col shadow-sm">
            {/* Header */}
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <div className="flex items-center gap-2">
                    {node ? (
                        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                            <Database className="h-4 w-4 text-primary" />
                        </div>
                    ) : (
                        <div className="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center">
                            <Link2 className="h-4 w-4 text-amber-600" />
                        </div>
                    )}
                    <div>
                        <h3 className="text-sm font-semibold text-slate-700">
                            {node ? `${t('components.detailPanel.nodeType')}: ${node.name}` : `${t('components.detailPanel.edgeType')}: ${edge?.relationship_type}`}
                        </h3>
                        {edge && <p className="text-[10px] text-slate-400">{edge.source} → {edge.target}</p>}
                    </div>
                </div>
                <button onClick={onClose} className="p-1.5 hover:bg-slate-200 rounded-full transition-colors">
                    <X className="h-4 w-4 text-slate-400" />
                </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-6">
                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <Loader2 className="h-6 w-6 animate-spin text-slate-300" />
                    </div>
                ) : node ? (
                    /* Node/Entity Mode */
                    <>
                        <section>
                            <div className="flex items-center justify-between mb-4">
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    className="h-8 px-2 text-primary hover:bg-primary/5"
                                    onClick={() => setIsAddingMapping(true)}
                                    disabled={isAddingMapping}
                                >
                                    <Plus className="h-4 w-4 mr-1" />
                                    {t('components.binding.addBinding')}
                                </Button>
                            </div>

                            {isAddingMapping && (
                                <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 mb-4 space-y-4 shadow-inner">
                                    <div className="space-y-2">
                                        <Label className="text-xs font-medium">{t('components.binding.selectProduct')}</Label>
                                        <Select onValueChange={handleProductSelect}>
                                            <SelectTrigger className="h-9 bg-white">
                                                <SelectValue placeholder={t('components.binding.selectProductPlaceholder')} />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {products.map(p => (
                                                    <SelectItem key={p.id} value={p.id.toString()}>{p.name}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    {fetchingSchema && (
                                        <div className="flex items-center gap-2 text-xs text-slate-400 py-2">
                                            <Loader2 className="h-3 w-3 animate-spin" />
                                            {t('components.binding.fetchingSchema')}
                                        </div>
                                    )}

                                    {selectedProductSchema && (
                                        <>
                                            <div className="space-y-2">
                                                <Label className="text-xs font-medium">{t('components.binding.mapToMessage')}</Label>
                                                <Select onValueChange={(v) => setNewMapping({ ...newMapping, grpc_message_type: v })}>
                                                    <SelectTrigger className="h-9 bg-white">
                                                        <SelectValue placeholder={t('components.binding.selectMessagePlaceholder')} />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {selectedProductSchema.message_types.map((m: any) => (
                                                            <SelectItem key={m.name} value={m.name}>{m.name}</SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            </div>

                                            <div className="space-y-2">
                                                <Label className="text-xs font-medium">{t('components.binding.listMethod')}</Label>
                                                <Select value={newMapping.list_method} onValueChange={(v) => setNewMapping({ ...newMapping, list_method: v })}>
                                                    <SelectTrigger className="h-9 bg-white">
                                                        <SelectValue placeholder={t('components.binding.selectMethodPlaceholder')} />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {selectedProductSchema.methods.map(m => (
                                                            <SelectItem key={m.name} value={m.name}>{m.name}</SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            </div>

                                            <div className="grid grid-cols-2 gap-3">
                                                <div className="space-y-2">
                                                    <Label className="text-xs font-medium">{t('components.binding.pkField')}</Label>
                                                    <Select value={newMapping.id_field_mapping} onValueChange={(v) => setNewMapping({ ...newMapping, id_field_mapping: v })}>
                                                        <SelectTrigger className="h-9 bg-white">
                                                            <SelectValue placeholder={t('components.binding.selectPkPlaceholder')} />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            {selectedProductSchema.message_types.find(mt => mt.name === newMapping.grpc_message_type)?.fields.map((f: any) => (
                                                                <SelectItem key={f.name} value={f.name}>{f.name}</SelectItem>
                                                            ))}
                                                        </SelectContent>
                                                    </Select>
                                                </div>
                                                <div className="space-y-2">
                                                    <Label className="text-xs font-medium">{t('components.binding.nameField')}</Label>
                                                    <Select value={newMapping.name_field_mapping} onValueChange={(v) => setNewMapping({ ...newMapping, name_field_mapping: v })}>
                                                        <SelectTrigger className="h-9 bg-white">
                                                            <SelectValue placeholder={t('components.binding.selectNamePlaceholder')} />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            {selectedProductSchema.message_types.find(mt => mt.name === newMapping.grpc_message_type)?.fields.map((f: any) => (
                                                                <SelectItem key={f.name} value={f.name}>{f.name}</SelectItem>
                                                            ))}
                                                        </SelectContent>
                                                    </Select>
                                                </div>
                                            </div>

                                            <div className="grid grid-cols-2 gap-3 pt-2">
                                                <Button variant="outline" size="sm" onClick={() => setIsAddingMapping(false)} className="h-9">{t('components.binding.cancel')}</Button>
                                                <Button
                                                    size="sm"
                                                    onClick={handleCreateEntityMapping}
                                                    className="h-9 bg-primary hover:opacity-90"
                                                    disabled={!newMapping.grpc_message_type}
                                                >
                                                    {t('components.binding.confirmBinding')}
                                                </Button>
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}

                            {entityMappings.length > 0 ? (
                                <div className="space-y-3">
                                    {entityMappings.map(m => (
                                        <div key={m.id} className="group border border-slate-200 rounded-lg p-3 hover:border-indigo-200 hover:shadow-sm transition-all bg-white">
                                            <div className="flex items-start justify-between mb-2">
                                                <div className="flex items-center gap-2">
                                                    <Badge variant="secondary" className="bg-primary/10 text-primary hover:bg-primary/20 border-primary/10">
                                                        {products.find(p => p.id === m.data_product_id)?.name || t('components.binding.unknownProduct')}
                                                    </Badge>
                                                    <ArrowRight className="h-3 w-3 text-slate-300" />
                                                    <span className="text-xs font-mono font-medium text-slate-600">{m.grpc_message_type}</span>
                                                </div>
                                                <button
                                                    onClick={() => handleDeleteEntityMapping(m.id)}
                                                    className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-500 transition-opacity"
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </button>
                                            </div>
                                            <div className="flex items-center gap-4 text-[10px] text-slate-400">
                                                <span className="flex items-center gap-1">
                                                    <Settings2 className="h-3 w-3" />
                                                    {t('components.binding.method')}: {m.list_method || t('common.notConfigured')}
                                                </span>
                                                <span className="flex items-center gap-1">
                                                    <CheckCircle2 className={`h-3 w-3 ${m.sync_enabled ? 'text-green-500' : 'text-slate-300'}`} />
                                                    {t('components.binding.sync')}: {m.sync_enabled ? t('components.binding.syncOn') : t('components.binding.syncOff')}
                                                </span>
                                            </div>

                                            {/* Property Mapping Section within each Entity Mapping */}
                                            <div className="mt-3 pt-3 border-t border-slate-50">
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="w-full justify-between h-7 px-2 text-[10px] hover:bg-slate-50"
                                                    onClick={() => activeMappingId === m.id ? setActiveMappingId(null) : handleLoadPropertyMappings(m.id)}
                                                >
                                                    <span className="flex items-center gap-1.5 font-medium">
                                                        {activeMappingId === m.id ? t('components.binding.collapseProperty') : t('components.binding.propertyMappingCount', { count: m.property_mapping_count })}
                                                    </span>
                                                    <Settings2 className={`h-3 w-3 transform transition-transform ${activeMappingId === m.id ? 'rotate-180' : ''}`} />
                                                </Button>

                                                {activeMappingId === m.id && (
                                                    <div className="mt-2 space-y-2 animate-in fade-in slide-in-from-top-1">
                                                        {propertyMappings.map(pm => (
                                                            <div key={pm.id} className="flex items-center justify-between text-[10px] bg-slate-50 rounded px-2 py-1.5 border border-slate-100 group/pm">
                                                                <div className="flex items-center gap-1.5 truncate">
                                                                    <span className="font-medium text-slate-600 truncate">{pm.ontology_property.split(':')[0]}</span>
                                                                    <ArrowRight className="h-2 w-2 text-slate-300" />
                                                                    <div className="flex items-center gap-1 min-w-0">
                                                                        <span className="font-mono text-primary truncate">{pm.grpc_field}</span>
                                                                        {pm.transform_expression && (
                                                                            <span className="text-[8px] bg-primary/10 text-primary px-1 rounded flex-shrink-0">
                                                                                {pm.transform_expression}
                                                                            </span>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                                <button onClick={() => handleDeletePropertyMapping(pm.id)} className="opacity-0 group-hover/pm:opacity-100 hover:text-red-500">
                                                                    <Trash2 className="h-3 w-3" />
                                                                </button>
                                                            </div>
                                                        ))}

                                                        {!isAddingProp ? (
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                className="w-full h-6 text-[10px] text-indigo-600 hover:text-indigo-700 font-normal"
                                                                onClick={() => setIsAddingProp(true)}
                                                            >
                                                                <Plus className="h-3 w-3 mr-1" />
                                                                {t('components.binding.addPropertyMapping')}
                                                            </Button>
                                                        ) : (
                                                            <div className="bg-white border rounded p-2 space-y-2 shadow-sm">
                                                                <div className="flex gap-2 items-center">
                                                                    <div className="flex-1 min-w-0">
                                                                        {!isCustomProp ? (
                                                                            <Select onValueChange={(v) => setNewProp({ ...newProp, ontology_property: v })}>
                                                                                <SelectTrigger className="h-7 text-[10px]">
                                                                                    <SelectValue placeholder={t('components.binding.ontologyProperty')} />
                                                                                </SelectTrigger>
                                                                                <SelectContent>
                                                                                    {node.dataProperties?.map(p => {
                                                                                        const [name, type] = p.split(':')
                                                                                        return (
                                                                                            <SelectItem key={p} value={name}>
                                                                                                <div className="flex justify-between w-full items-center gap-2">
                                                                                                    <span>{name}</span>
                                                                                                    <span className="text-[9px] text-slate-400 bg-slate-100 px-1 rounded">
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
                                                                                className="h-7 text-[10px]"
                                                                                placeholder={t('components.binding.enterPropertyName')}
                                                                                value={newProp.ontology_property}
                                                                                onChange={(e) => setNewProp({ ...newProp, ontology_property: e.target.value })}
                                                                            />
                                                                        )}
                                                                    </div>
                                                                    <Button
                                                                        variant="ghost"
                                                                        size="icon"
                                                                        className="h-7 w-7 shrink-0"
                                                                        title={isCustomProp ? t('components.binding.selectExistingProp') : t('components.binding.manualInputProp')}
                                                                        onClick={() => setIsCustomProp(!isCustomProp)}
                                                                    >
                                                                        {isCustomProp ? <Settings2 className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
                                                                    </Button>
                                                                </div>

                                                                <Select onValueChange={(v) => setNewProp({ ...newProp, grpc_field: v })}>
                                                                    <SelectTrigger className="h-7 text-[10px]">
                                                                        <SelectValue placeholder={t('components.binding.grpcField')} />
                                                                    </SelectTrigger>
                                                                    <SelectContent>
                                                                        {selectedProductSchema?.message_types.find(mt => mt.name === m.grpc_message_type)?.fields.map((f: any) => (
                                                                            <SelectItem key={f.name} value={f.name}>{f.name}</SelectItem>
                                                                        ))}
                                                                    </SelectContent>
                                                                </Select>

                                                                <Select value={newProp.transformation} onValueChange={(v) => setNewProp({ ...newProp, transformation: v })}>
                                                                    <SelectTrigger className="h-7 text-[10px]">
                                                                        <SelectValue placeholder={t('components.binding.transformMethod')} />
                                                                    </SelectTrigger>
                                                                    <SelectContent>
                                                                        {TRANSFORMATION_OPTIONS.map(opt => (
                                                                            <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                                                                        ))}
                                                                    </SelectContent>
                                                                </Select>

                                                                <div className="flex gap-2">
                                                                    <Button variant="outline" size="sm" onClick={() => setIsAddingProp(false)} className="h-7 flex-1 text-[10px]">{t('components.binding.cancel')}</Button>
                                                                    <Button size="sm" onClick={handleCreatePropertyMapping} className="h-7 flex-1 text-[10px] bg-primary hover:opacity-90">{t('components.binding.add')}</Button>
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : !isAddingMapping && (
                                <div className="flex flex-col items-center justify-center py-8 text-slate-400 border border-dashed border-slate-200 rounded-lg bg-slate-50/50">
                                    <Database className="h-8 w-8 mb-2 opacity-20" />
                                    <p className="text-xs italic">{t('components.binding.noBindingDesc')}</p>
                                </div>
                            )}
                        </section>

                        <Separator />

                        <section>
                            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">{t('components.binding.ontologyProperty')}</h4>
                            <div className="space-y-1.5">
                                {node.dataProperties?.map((prop, i) => (
                                    <div key={i} className="flex items-center justify-between px-3 py-2 bg-slate-50 rounded-md border border-slate-100">
                                        <span className="text-xs font-medium text-slate-600">{prop}</span>
                                        {/* Placeholder for property mapping configuration */}
                                        <Badge variant="outline" className="text-[10px] h-4 font-normal text-slate-400 border-slate-200">
                                            {t('components.binding.unassignedField')}
                                        </Badge>
                                    </div>
                                )) || <p className="text-xs text-slate-400 italic">{t('components.binding.noPropDesc')}</p>}
                            </div>
                        </section>
                    </>
                ) : (
                    /* Edge/Relationship Mode */
                    <>
                        <section>
                            <div className="flex items-center justify-between mb-4">
                                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">{t('components.binding.relationshipBinding')}</h4>
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    className="h-8 px-2 text-amber-600 hover:text-amber-700 hover:bg-amber-50"
                                    onClick={() => setIsAddingRel(true)}
                                    disabled={isAddingRel || sourceMappings.length === 0 || targetMappings.length === 0}
                                >
                                    <Plus className="h-4 w-4 mr-1" />
                                    {t('components.binding.configRelationship')}
                                </Button>
                            </div>

                            {isAddingRel && (
                                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 mb-4 space-y-4 shadow-inner">
                                    <div className="grid gap-4">
                                        <div className="space-y-2">
                                            <Label className="text-xs font-medium">{t('components.binding.sourceEntity')}</Label>
                                            <Select onValueChange={(v) => {
                                                setNewRel({ ...newRel, source_entity_mapping_id: v })
                                                // Reset FK when source mapping changes
                                            }}>
                                                <SelectTrigger className="h-9 bg-white">
                                                    <SelectValue placeholder={t('components.binding.selectSourcePlaceholder')} />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {sourceMappings.map(m => (
                                                        <SelectItem key={m.id} value={m.id.toString()}>
                                                            {products.find(p => p.id === m.data_product_id)?.name} ({m.grpc_message_type})
                                                        </SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                        </div>

                                        <div className="space-y-2">
                                            <Label className="text-xs font-medium">{t('components.binding.targetEntity')}</Label>
                                            <Select onValueChange={(v) => setNewRel({ ...newRel, target_entity_mapping_id: v })}>
                                                <SelectTrigger className="h-9 bg-white">
                                                    <SelectValue placeholder={t('components.binding.selectTargetPlaceholder')} />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {targetMappings.map(m => (
                                                        <SelectItem key={m.id} value={m.id.toString()}>
                                                            {products.find(p => p.id === m.data_product_id)?.name} ({m.grpc_message_type})
                                                        </SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                        </div>

                                        <div className="space-y-2">
                                            <Label className="text-xs font-medium">{t('components.binding.sourceFkField')}</Label>
                                            <Select value={newRel.source_fk_field} onValueChange={(v) => setNewRel({ ...newRel, source_fk_field: v })}>
                                                <SelectTrigger className="h-9 bg-white">
                                                    <SelectValue placeholder={t('components.binding.selectFkPlaceholder')} />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {(() => {
                                                        const mapping = sourceMappings.find(m => m.id.toString() === newRel.source_entity_mapping_id?.toString())
                                                        if (!mapping || !sourceSchema) return null
                                                        const msgType = sourceSchema.message_types.find(mt => mt.name === mapping.grpc_message_type)
                                                        return msgType?.fields.map((f: any) => (
                                                            <SelectItem key={f.name} value={f.name}>{f.name} ({f.type})</SelectItem>
                                                        ))
                                                    })()}
                                                </SelectContent>
                                            </Select>
                                            <p className="text-[10px] text-slate-400">{t('components.binding.fkDesc')}</p>
                                        </div>

                                        <div className="space-y-2">
                                            <Label className="text-xs font-medium">{t('components.binding.targetMatchField')}</Label>
                                            <Select value={newRel.target_id_field} onValueChange={(v) => setNewRel({ ...newRel, target_id_field: v })}>
                                                <SelectTrigger className="h-9 bg-white">
                                                    <SelectValue placeholder={t('components.binding.selectMatchPlaceholder')} />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {(() => {
                                                        const mapping = targetMappings.find(m => m.id.toString() === newRel.target_entity_mapping_id?.toString())
                                                        if (!mapping || !targetSchema) return null
                                                        const msgType = targetSchema.message_types.find(mt => mt.name === mapping.grpc_message_type)
                                                        return msgType?.fields.map((f: any) => (
                                                            <SelectItem key={f.name} value={f.name}>{f.name} ({f.type})</SelectItem>
                                                        ))
                                                    })()}
                                                </SelectContent>
                                            </Select>
                                            <p className="text-[10px] text-slate-400">{t('components.binding.matchDesc')}</p>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-3 pt-2">
                                        <Button variant="outline" size="sm" onClick={() => setIsAddingRel(false)} className="h-9">{t('components.binding.cancel')}</Button>
                                        <Button
                                            size="sm"
                                            onClick={handleCreateRelMapping}
                                            className="h-9 bg-primary hover:opacity-90"
                                            disabled={!newRel.source_entity_mapping_id || !newRel.target_entity_mapping_id || !newRel.source_fk_field}
                                        >
                                            {t('components.binding.confirmBinding')}
                                        </Button>
                                    </div>
                                </div>
                            )}

                            {relMappings.length > 0 ? (
                                <div className="space-y-3">
                                    {relMappings.map(r => (
                                        <div key={r.id} className="group border border-slate-200 rounded-lg p-3 hover:border-amber-200 bg-white">
                                            <div className="flex items-center justify-between mb-3">
                                                <div className="flex items-center gap-1.5 overflow-hidden">
                                                    <span className="text-[10px] font-medium text-slate-500 truncate">{r.source_ontology_class}</span>
                                                    <div className="h-px w-4 bg-slate-200" />
                                                    <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200 text-[10px] px-1.5 h-4">
                                                        {r.ontology_relationship}
                                                    </Badge>
                                                    <div className="h-px w-4 bg-slate-200" />
                                                    <span className="text-[10px] font-medium text-slate-500 truncate">{r.target_ontology_class}</span>
                                                </div>
                                                <button
                                                    onClick={() => handleDeleteRelMapping(r.id)}
                                                    className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-500 transition-opacity"
                                                >
                                                    <Trash2 className="h-3.5 w-3.5" />
                                                </button>
                                            </div>
                                            <div className="bg-slate-50 rounded-md p-2 border border-slate-100">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-[10px] text-slate-400">{t('components.binding.assocPath')}:</span>
                                                    <span className="text-[10px] font-mono text-slate-700 bg-white px-1.5 py-0.5 rounded border border-slate-100">
                                                        {r.source_fk_field} → {r.target_id_field}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : !isAddingRel && (
                                <div className="flex flex-col items-center justify-center py-8 text-slate-400 border border-dashed border-slate-200 rounded-lg bg-slate-50/50">
                                    <Link2 className="h-8 w-8 mb-2 opacity-20" />
                                    <p className="text-xs italic">{t('components.binding.noRelBinding')}</p>
                                    {(sourceMappings.length === 0 || targetMappings.length === 0) && (
                                        <div className="mt-2 flex items-center gap-1 text-[10px] text-amber-500">
                                            <AlertCircle className="h-3 w-3" />
                                            <span>{t('components.binding.bindNodesFirst')}</span>
                                        </div>
                                    )}
                                </div>
                            )}
                        </section>
                    </>
                )
                }
            </div >

            <div className="p-4 border-t border-slate-100 bg-slate-50/30">
                <div className="flex items-center justify-between text-[10px] text-slate-400">
                    <span className="flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3 text-green-500" />
                        {t('components.binding.connected')}
                    </span>
                    <span className="flex items-center gap-1">
                        <Settings2 className="h-3 w-3" />
                        {t('components.binding.realtimeSave')}
                    </span>
                </div>
            </div>
        </div >
    )
}
