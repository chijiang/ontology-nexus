'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { AppLayout } from '@/components/layout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog'
import { useAuthStore } from '@/lib/auth'
import {
    rulesApi,
    actionsApi,
    RuleInfo,
    RuleDetail,
    ActionInfo,
    ActionDetail,
    ActionParameter,
} from '@/lib/api'
import { toast } from 'sonner'
import {
    Plus,
    Edit,
    Trash2,
    Code,
    Layers,
    Zap,
    AlertTriangle,
    CheckCircle,
    XCircle,
    RefreshCw,
    Play,
    Settings,
    Minus,
} from 'lucide-react'
import BusinessEditor, { Schema, parseActionSignature } from '@/components/business-editor'
import { graphApi } from '@/lib/api'

// Rule card component
function RuleCard({
    rule,
    onEdit,
    onDelete,
}: {
    rule: RuleInfo
    onEdit: () => void
    onDelete: () => void
}) {
    const t = useTranslations('rules')
    const tCommon = useTranslations('common')

    return (
        <Card className="group hover:shadow-lg transition-all duration-200 border-slate-200 hover:border-indigo-300">
            <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                        <div className="p-2 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600">
                            <Zap className="h-4 w-4 text-white" />
                        </div>
                        <div>
                            <CardTitle className="text-base font-semibold text-slate-800">
                                {rule.name}
                            </CardTitle>
                            <p className="text-xs text-slate-500 mt-0.5">
                                {t('priority')}: {rule.priority}
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={onEdit}
                            className="h-8 w-8 p-0 text-slate-500 hover:text-indigo-600"
                            title={tCommon('edit')}
                        >
                            <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={onDelete}
                            className="h-8 w-8 p-0 text-slate-500 hover:text-red-600"
                            title={tCommon('delete')}
                        >
                            <Trash2 className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="pt-0">
                <div className="flex flex-wrap gap-2">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        ON {rule.trigger.type}
                    </span>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
                        {rule.trigger.entity}
                        {rule.trigger.property && `.${rule.trigger.property}`}
                    </span>
                    {rule.is_active ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            {t('active')}
                        </span>
                    ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                            <XCircle className="h-3 w-3 mr-1" />
                            {t('inactive')}
                        </span>
                    )}
                </div>
            </CardContent>
        </Card>
    )
}

// Action card component
function ActionCard({
    action,
    onEdit,
    onDelete,
}: {
    action: ActionInfo
    onEdit: () => void
    onDelete: () => void
}) {
    const t = useTranslations('rules')
    const tCommon = useTranslations('common')

    return (
        <Card className="group hover:shadow-lg transition-all duration-200 border-slate-200 hover:border-emerald-300">
            <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                        <div className="p-2 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600">
                            <Play className="h-4 w-4 text-white" />
                        </div>
                        <div>
                            <CardTitle className="text-base font-semibold text-slate-800">
                                {action.name}
                            </CardTitle>
                            <p className="text-xs text-slate-500 mt-0.5">
                                {action.entity_type}
                            </p>
                            {action.description && (
                                <p className="text-[10px] text-slate-400 mt-1 italic line-clamp-2">
                                    {action.description}
                                </p>
                            )}
                        </div>
                    </div>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={onEdit}
                            className="h-8 w-8 p-0 text-slate-500 hover:text-emerald-600"
                            title={tCommon('edit')}
                        >
                            <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={onDelete}
                            className="h-8 w-8 p-0 text-slate-500 hover:text-red-600"
                            title={tCommon('delete')}
                        >
                            <Trash2 className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="pt-0">
                <div className="flex flex-wrap gap-2">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                        ACTION
                    </span>
                    {action.is_active ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            {t('active')}
                        </span>
                    ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                            <XCircle className="h-3 w-3 mr-1" />
                            {t('inactive')}
                        </span>
                    )}
                </div>
            </CardContent>
        </Card>
    )
}

// DSL Editor component
function DslEditor({
    value,
    onChange,
    error,
    placeholder,
}: {
    value: string
    onChange: (value: string) => void
    error?: string
    placeholder?: string
}) {
    return (
        <div className="space-y-2">
            <div className="relative">
                <textarea
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    placeholder={placeholder}
                    className={`w-full h-96 p-4 font-mono text-sm rounded-lg border ${error
                        ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                        : 'border-slate-300 focus:border-indigo-500 focus:ring-indigo-500'
                        } focus:ring-2 focus:ring-opacity-50 resize-none bg-slate-50`}
                    style={{ lineHeight: '1.6' }}
                />
                <div className="absolute top-2 right-2 flex items-center gap-2">
                    <span className="text-xs text-slate-400 bg-white px-2 py-0.5 rounded">
                        DSL
                    </span>
                </div>
            </div>
            {error && (
                <div className="flex items-start gap-2 text-red-600 text-sm">
                    <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                    <span>{error}</span>
                </div>
            )}
        </div>
    )
}

// Rule Editor Dialog
function RuleEditorDialog({
    open,
    onClose,
    rule,
    onSave,
}: {
    open: boolean
    onClose: () => void
    rule: RuleDetail | null
    onSave: () => void
}) {
    const t = useTranslations('rules')
    const tCommon = useTranslations('common')
    const [name, setName] = useState('')
    const [priority, setPriority] = useState(0)
    const [isActive, setIsActive] = useState(true)
    const [dslContent, setDslContent] = useState('')
    const [error, setError] = useState('')
    const [saving, setSaving] = useState(false)
    const [activeTab, setActiveTab] = useState('dsl')
    const [schema, setSchema] = useState<Schema>({ nodes: [], relationships: [] })
    const [trigger, setTrigger] = useState<{
        type: string
        entity: string
        property: string | null
    }>({
        type: 'UPDATE',
        entity: 'Entity',
        property: ''
    })
    const [isCustomProperty, setIsCustomProperty] = useState(false)
    const token = useAuthStore((state) => state.token)

    useEffect(() => {
        if (rule) {
            setName(rule.name)
            setPriority(rule.priority)
            setIsActive(rule.is_active)
            setDslContent(rule.dsl_content)
            setTrigger(rule.trigger)
            // If property is not in current schema's entity properties, it might be custom
            const properties = schema.nodes.find(n => n.name === rule.trigger.entity)?.dataProperties || []
            if (rule.trigger.property && !properties.includes(rule.trigger.property)) {
                setIsCustomProperty(true)
            } else {
                setIsCustomProperty(false)
            }
        } else {
            setName('')
            setPriority(100)
            setIsActive(true)
            setIsCustomProperty(false)
            setTrigger({
                type: 'UPDATE',
                entity: 'Entity',
                property: ''
            })
            setDslContent(`// ${t('newRuleExample')}
RULE NewRule PRIORITY 100 {
    ON UPDATE(Entity.property)
    FOR (e: Entity WHERE e.status == "Active") {
        SET e.processedAt = NOW();
    }
}
`)
        }
        setError('')

        // Fetch schema when opening
        if (open && token) {
            graphApi.getSchema(token).then(res => {
                setSchema(res.data)
            }).catch(console.error)
        }
    }, [rule, open, token])

    const handleSave = async () => {
        setError('')
        setSaving(true)

        try {
            if (rule) {
                // Update existing rule
                await rulesApi.update(rule.name, {
                    dsl_content: dslContent,
                    priority,
                    is_active: isActive,
                })
                toast.success(t('ruleUpdated'))
            } else {
                // Create new rule
                if (!name.trim()) {
                    setError(t('inputRuleName'))
                    setSaving(false)
                    return
                }
                await rulesApi.create({
                    name: name.trim(),
                    dsl_content: dslContent,
                    priority,
                    is_active: isActive,
                })
                toast.success(t('ruleCreated'))
            }
            onSave()
            onClose()
        } catch (err: any) {
            const message = err.response?.data?.detail || t('operationFailed')
            setError(message)
            toast.error(message)
        } finally {
            setSaving(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-6xl max-h-[95vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Zap className="h-5 w-5 text-indigo-600" />
                        {rule ? t('editRule') : t('createRule')}
                    </DialogTitle>
                    <DialogDescription>
                        {t('useDsl')}
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-slate-700">
                                {t('ruleName')}
                            </label>
                            <Input
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder={t('ruleNamePlaceholder')}
                                disabled={!!rule}
                                className={rule ? 'bg-slate-100' : ''}
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-slate-700">
                                {t('priority')}
                            </label>
                            <Input
                                type="number"
                                value={priority}
                                onChange={(e) => setPriority(parseInt(e.target.value) || 0)}
                                placeholder={t('priorityPlaceholder')}
                            />
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <input
                            type="checkbox"
                            id="isActive"
                            checked={isActive}
                            onChange={(e) => setIsActive(e.target.checked)}
                            className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        <label htmlFor="isActive" className="text-sm text-slate-700">
                            {t('activateRule')}
                        </label>
                    </div>

                    <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                        <TabsList className="grid w-full grid-cols-2 mb-4">
                            <TabsTrigger value="dsl" className="flex items-center gap-2">
                                <Code className="h-4 w-4" /> {t('dslEditor')}
                            </TabsTrigger>
                            <TabsTrigger value="business" className="flex items-center gap-2">
                                <Layers className="h-4 w-4" /> {t('businessEditor')}
                            </TabsTrigger>
                        </TabsList>

                        <TabsContent value="dsl">
                            <div className="space-y-4">
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-slate-700">
                                        {t('dslContent')}
                                    </label>
                                    <DslEditor
                                        value={dslContent}
                                        onChange={setDslContent}
                                        error={error}
                                        placeholder={t('dslPlaceholder')}
                                    />
                                </div>

                                {/* DSL Help */}
                                <div className="bg-slate-50 rounded-lg p-4 text-sm">
                                    <h4 className="font-medium text-slate-700 mb-2">{t('dslSyntax')}</h4>
                                    <div className="grid grid-cols-2 gap-4 text-slate-600">
                                        <div>
                                            <p className="font-mono text-xs bg-white px-2 py-1 rounded mb-1">
                                                {t('triggerOnUpdate')}
                                            </p>
                                            <p className="text-xs">{t('triggerOnUpdateDesc')}</p>
                                        </div>
                                        <div>
                                            <p className="font-mono text-xs bg-white px-2 py-1 rounded mb-1">
                                                {t('scopeDefinition')}
                                            </p>
                                            <p className="text-xs">{t('scopeDefinitionDesc')}</p>
                                        </div>
                                        <div>
                                            <p className="font-mono text-xs bg-white px-2 py-1 rounded mb-1">
                                                {t('setProperty')}
                                            </p>
                                            <p className="text-xs">{t('setPropertyDesc')}</p>
                                        </div>
                                        <div>
                                            <p className="font-mono text-xs bg-white px-2 py-1 rounded mb-1">
                                                {t('triggerAction')}
                                            </p>
                                            <p className="text-xs">{t('triggerActionDesc')}</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </TabsContent>

                        <TabsContent value="business">
                            <div className="space-y-6">
                                <div className="p-4 bg-amber-50 rounded-lg border border-amber-100">
                                    <h4 className="text-xs font-bold text-amber-800 uppercase mb-3 flex items-center gap-1.5">
                                        <Zap size={14} /> {t('triggerConfig')}
                                    </h4>
                                    <div className="grid grid-cols-3 gap-3">
                                        <div className="space-y-1.5">
                                            <label className="text-[10px] font-bold text-amber-700 uppercase">{t('triggerType')}</label>
                                            <select
                                                value={trigger.type}
                                                onChange={(e) => setTrigger({ ...trigger, type: e.target.value })}
                                                className="w-full bg-white border border-amber-200 text-slate-700 text-xs rounded px-2 py-1.5 outline-none"
                                            >
                                                <option value="UPDATE">UPDATE</option>
                                                <option value="CREATE">CREATE</option>
                                                <option value="DELETE">DELETE</option>
                                            </select>
                                        </div>
                                        <div className="space-y-1.5">
                                            <label className="text-[10px] font-bold text-amber-700 uppercase">{t('entityType')}</label>
                                            <select
                                                value={trigger.entity}
                                                onChange={(e) => setTrigger({ ...trigger, entity: e.target.value, property: '' })}
                                                className="w-full bg-white border border-amber-200 text-slate-700 text-xs rounded px-2 py-1.5 outline-none"
                                            >
                                                <option value="">{t('selectEntity')}</option>
                                                {schema.nodes.map(n => <option key={n.name} value={n.name}>{n.name}</option>)}
                                            </select>
                                        </div>
                                        <div className="space-y-1.5">
                                            <label className="text-[10px] font-bold text-amber-700 uppercase">{t('triggerProperty')}</label>
                                            {!isCustomProperty ? (
                                                <select
                                                    value={trigger.property || ''}
                                                    onChange={(e) => {
                                                        if (e.target.value === '__custom__') {
                                                            setIsCustomProperty(true)
                                                            setTrigger({ ...trigger, property: '' })
                                                        } else {
                                                            setTrigger({ ...trigger, property: e.target.value })
                                                        }
                                                    }}
                                                    disabled={trigger.type !== 'UPDATE'}
                                                    className="w-full bg-white border border-amber-200 text-slate-700 text-xs rounded px-2 py-1.5 outline-none disabled:bg-amber-50/50 disabled:text-amber-300"
                                                >
                                                    <option value="">{t('allProperties')}</option>
                                                    {schema.nodes.find(n => n.name === trigger.entity)?.dataProperties.map(p => (
                                                        <option key={p} value={p}>{p}</option>
                                                    ))}
                                                    <option value="__custom__" className="text-indigo-600 font-medium">{t('custom')}</option>
                                                </select>
                                            ) : (
                                                <div className="flex gap-1">
                                                    <Input
                                                        value={trigger.property || ''}
                                                        onChange={(e) => setTrigger({ ...trigger, property: e.target.value })}
                                                        className="h-7 text-xs py-1 px-2 border-amber-200 focus:ring-amber-500 focus:ring-1 outline-none"
                                                        placeholder={t('inputProperty')}
                                                        autoFocus
                                                    />
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        className="h-7 px-1.5 text-amber-600 hover:bg-amber-100 text-[10px]"
                                                        onClick={() => {
                                                            setIsCustomProperty(false)
                                                            setTrigger({ ...trigger, property: '' })
                                                        }}
                                                    >
                                                        {t('cancel')}
                                                    </Button>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                <BusinessEditor
                                    mode="RULE"
                                    initialDsl={dslContent}
                                    schema={schema}
                                    meta={{ name, priority, trigger }}
                                    onDslChange={setDslContent}
                                />
                            </div>
                        </TabsContent>
                    </Tabs>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={onClose} disabled={saving}>
                        {tCommon('cancel')}
                    </Button>
                    <Button onClick={handleSave} disabled={saving}>
                        {saving ? (
                            <>
                                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                                {tCommon('loading')}
                            </>
                        ) : (
                            tCommon('save')
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}

// Action Editor Dialog
function ActionEditorDialog({
    open,
    onClose,
    action,
    onSave,
}: {
    open: boolean
    onClose: () => void
    action: ActionDetail | null
    onSave: () => void
}) {
    const t = useTranslations('rules')
    const tCommon = useTranslations('common')
    const [name, setName] = useState('')
    const [entityType, setEntityType] = useState('')
    const [isActive, setIsActive] = useState(true)
    const [description, setDescription] = useState('')
    const [dslContent, setDslContent] = useState('')
    const [error, setError] = useState('')
    const [parameters, setParameters] = useState<ActionParameter[]>([])
    const [saving, setSaving] = useState(false)
    const [activeTab, setActiveTab] = useState('dsl')
    const [schema, setSchema] = useState<Schema>({ nodes: [], relationships: [] })
    const token = useAuthStore((state) => state.token)

    useEffect(() => {
        if (action) {
            setName(action.name)
            setDslContent(action.dsl_content)
            setDescription(action.description || '')

            // Extract base name and parameters from signature if needed
            // But ActionDef already has structured parameters if we fetch it from registry
            // For now, let's parse the signature from the name or DSL
            const match = action.name.match(/^([^.(]+)\.(.+)$/)
            if (match) {
                setEntityType(match[1])
                const fullActionName = match[2]

                // Check if fullActionName has parameters
                const paramMatch = fullActionName.match(/^([^()]+)\((.*)\)$/)
                if (paramMatch) {
                    setName(paramMatch[1])
                    // Parameters are usually in the action details if we use a different API, 
                    // but here we can parse from DSL as the source of truth
                } else {
                    setName(fullActionName)
                }
            }

            // Sync parameters from DSL
            const sig = parseActionSignature(action.dsl_content)
            if (sig) {
                setParameters(sig.parameters)
            }
        } else {
            setName('')
            setEntityType('')
            setIsActive(true)
            setParameters([])
            setDslContent(`// ${t('newActionExample')}
ACTION Entity.submit {
    PRECONDITION statusCheck: this.status == "Draft"
        ON_FAILURE: "Only draft items can be submitted"
    EFFECT {
        SET this.status = "Submitted";
        SET this.submittedAt = NOW();
    }
}
`)
        }
        setError('')

        // Fetch schema when opening
        if (open && token) {
            graphApi.getSchema(token).then(res => {
                setSchema(res.data)
            }).catch(console.error)
        }
    }, [action, open, token])

    const handleSave = async () => {
        setError('')
        setSaving(true)

        try {
            if (action) {
                // Update existing action
                const fullName = `${entityType.trim()}.${name.trim()}`
                await actionsApi.update(action.name, {
                    dsl_content: dslContent,
                    is_active: isActive,
                })
                toast.success(t('actionUpdated'))
            } else {
                // Create new action
                if (!name.trim()) {
                    setError(t('inputActionName'))
                    setSaving(false)
                    return
                }
                if (!entityType.trim()) {
                    setError(t('inputEntityType'))
                    setSaving(false)
                    return
                }
                const fullName = `${entityType.trim()}.${name.trim()}`
                await actionsApi.create({
                    name: fullName,
                    entity_type: entityType.trim(),
                    dsl_content: dslContent,
                    is_active: isActive,
                })
                toast.success(t('actionCreated'))
            }
            onSave()
            onClose()
        } catch (err: any) {
            const message = err.response?.data?.detail || t('operationFailed')
            setError(message)
            toast.error(message)
        } finally {
            setSaving(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-6xl max-h-[95vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Play className="h-5 w-5 text-emerald-600" />
                        {action ? t('editAction') : t('createAction')}
                    </DialogTitle>
                    <DialogDescription>
                        {t('useActionDsl')}
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-slate-700">
                                {t('actionName')}
                            </label>
                            <Input
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder={t('actionNamePlaceholder')}
                                disabled={!!action}
                                className={action ? 'bg-slate-100' : ''}
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-slate-700">
                                {t('actionEntityType')}
                            </label>
                            <Input
                                value={entityType}
                                onChange={(e) => setEntityType(e.target.value)}
                                placeholder={t('entityTypePlaceholder')}
                                disabled={!!action}
                                className={action ? 'bg-slate-100' : ''}
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-700">
                            {t('actionDesc')}
                        </label>
                        <Input
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder={t('actionDescPlaceholder')}
                        />
                    </div>

                    {/* Parameters Section */}
                    <div className="space-y-3 p-4 bg-slate-50 rounded-lg border border-slate-200">
                        <div className="flex items-center justify-between">
                            <label className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                                <Layers className="h-4 w-4 text-indigo-500" />
                                {t('actionParams')}
                            </label>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setParameters([...parameters, { name: '', type: 'string', optional: false }])}
                                className="h-7 text-xs"
                            >
                                <Plus className="h-3 w-3 mr-1" /> {t('addParam')}
                            </Button>
                        </div>

                        {parameters.length === 0 ? (
                            <p className="text-xs text-slate-400 italic">{t('noParams')}</p>
                        ) : (
                            <div className="space-y-2">
                                {parameters.map((param, index) => (
                                    <div key={index} className="flex items-center gap-2 bg-white p-2 rounded border border-slate-100 shadow-sm">
                                        <div className="flex-1">
                                            <Input
                                                value={param.name}
                                                onChange={(e) => {
                                                    const newParams = [...parameters]
                                                    newParams[index].name = e.target.value
                                                    setParameters(newParams)
                                                }}
                                                placeholder={t('paramName')}
                                                className="h-8 text-xs font-mono"
                                            />
                                        </div>
                                        <div className="w-32">
                                            <select
                                                value={param.type}
                                                onChange={(e) => {
                                                    const newParams = [...parameters]
                                                    newParams[index].type = e.target.value
                                                    setParameters(newParams)
                                                }}
                                                className="w-full h-8 text-xs rounded border border-slate-200 bg-transparent px-2"
                                            >
                                                <option value="string">string</option>
                                                <option value="number">number</option>
                                                <option value="boolean">boolean</option>
                                                <option value="datetime">datetime</option>
                                                <option value="any">any</option>
                                            </select>
                                        </div>
                                        <div className="flex items-center gap-1 min-w-[60px]">
                                            <input
                                                type="checkbox"
                                                checked={param.optional}
                                                onChange={(e) => {
                                                    const newParams = [...parameters]
                                                    newParams[index].optional = e.target.checked
                                                    setParameters(newParams)
                                                }}
                                                className="h-3 w-3 rounded border-slate-300 text-emerald-600"
                                            />
                                            <label className="text-[10px] text-slate-500">{tCommon('optional')}</label>
                                        </div>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            onClick={() => setParameters(parameters.filter((_, i) => i !== index))}
                                            className="h-8 w-8 text-slate-400 hover:text-red-500 hover:bg-red-50"
                                        >
                                            <Minus className="h-4 w-4" />
                                        </Button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <div className="flex items-center gap-2">
                        <input
                            type="checkbox"
                            id="actionIsActive"
                            checked={isActive}
                            onChange={(e) => setIsActive(e.target.checked)}
                            className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                        />
                        <label htmlFor="actionIsActive" className="text-sm text-slate-700">
                            {t('activateAction')}
                        </label>
                    </div>

                    <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                        <TabsList className="grid w-full grid-cols-2 mb-4">
                            <TabsTrigger value="dsl" className="flex items-center gap-2">
                                <Code className="h-4 w-4" /> {t('dslEditor')}
                            </TabsTrigger>
                            <TabsTrigger value="business" className="flex items-center gap-2">
                                <Layers className="h-4 w-4" /> {t('businessEditor')}
                            </TabsTrigger>
                        </TabsList>

                        <TabsContent value="dsl">
                            <div className="space-y-4">
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-slate-700">
                                        {t('dslContent')}
                                    </label>
                                    <DslEditor
                                        value={dslContent}
                                        onChange={setDslContent}
                                        error={error}
                                        placeholder={t('actionDslPlaceholder')}
                                    />
                                </div>

                                {/* DSL Help */}
                                <div className="bg-slate-50 rounded-lg p-4 text-sm">
                                    <h4 className="font-medium text-slate-700 mb-2">{t('dslSyntax')}</h4>
                                    <div className="grid grid-cols-2 gap-4 text-slate-600">
                                        <div>
                                            <p className="font-mono text-xs bg-white px-2 py-1 rounded mb-1">
                                                {t('precondition')}
                                            </p>
                                            <p className="text-xs">{t('preconditionDesc')}</p>
                                        </div>
                                        <div>
                                            <p className="font-mono text-xs bg-white px-2 py-1 rounded mb-1">
                                                {t('onFailure')}
                                            </p>
                                            <p className="text-xs">{t('onFailureDesc')}</p>
                                        </div>
                                        <div>
                                            <p className="font-mono text-xs bg-white px-2 py-1 rounded mb-1">
                                                {t('effect')}
                                            </p>
                                            <p className="text-xs">{t('effectDesc')}</p>
                                        </div>
                                        <div>
                                            <p className="font-mono text-xs bg-white px-2 py-1 rounded mb-1">
                                                {t('setEntityProperty')}
                                            </p>
                                            <p className="text-xs">{t('setEntityPropertyDesc')}</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </TabsContent>

                        <TabsContent value="business">
                            <div className="space-y-6">
                                <BusinessEditor
                                    mode="ACTION"
                                    initialDsl={dslContent}
                                    schema={schema}
                                    meta={{ name, entityType, description, parameters }}
                                    onDslChange={setDslContent}
                                />
                            </div>
                        </TabsContent>
                    </Tabs>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={onClose} disabled={saving}>
                        {tCommon('cancel')}
                    </Button>
                    <Button
                        onClick={handleSave}
                        disabled={saving}
                        className="bg-emerald-600 hover:bg-emerald-700"
                    >
                        {saving ? (
                            <>
                                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                                {tCommon('loading')}
                            </>
                        ) : (
                            tCommon('save')
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}

// Delete confirmation dialog
function DeleteConfirmDialog({
    open,
    onClose,
    onConfirm,
    itemName,
    itemType,
}: {
    open: boolean
    onClose: () => void
    onConfirm: () => void
    itemName: string
    itemType: 'rule' | 'action'
}) {
    const t = useTranslations('rules')
    const tCommon = useTranslations('common')
    const [deleting, setDeleting] = useState(false)

    const handleConfirm = async () => {
        setDeleting(true)
        try {
            await onConfirm()
        } finally {
            setDeleting(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 text-red-600">
                        <AlertTriangle className="h-5 w-5" />
                        {t('confirmDelete')}
                    </DialogTitle>
                    <DialogDescription>
                        {itemType === 'rule'
                            ? t('confirmDeleteRule', { name: itemName })
                            : t('confirmDeleteAction', { name: itemName })
                        }
                    </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                    <Button variant="outline" onClick={onClose} disabled={deleting}>
                        {tCommon('cancel')}
                    </Button>
                    <Button
                        variant="destructive"
                        onClick={handleConfirm}
                        disabled={deleting}
                    >
                        {deleting ? (
                            <>
                                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                                {t('deleting')}
                            </>
                        ) : (
                            tCommon('delete')
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}

// Main page component
export default function RulesPage() {
    const router = useRouter()
    const t = useTranslations('rules')
    const tCommon = useTranslations('common')
    const token = useAuthStore((state) => state.token)
    const [isHydrated, setIsHydrated] = useState(false)
    const [activeTab, setActiveTab] = useState('rules')

    // Rules state
    const [rules, setRules] = useState<RuleInfo[]>([])
    const [rulesLoading, setRulesLoading] = useState(false)
    const [ruleEditorOpen, setRuleEditorOpen] = useState(false)
    const [editingRule, setEditingRule] = useState<RuleDetail | null>(null)
    const [deletingRule, setDeletingRule] = useState<RuleInfo | null>(null)

    // Actions state
    const [actions, setActions] = useState<ActionInfo[]>([])
    const [actionsLoading, setActionsLoading] = useState(false)
    const [actionEditorOpen, setActionEditorOpen] = useState(false)
    const [editingAction, setEditingAction] = useState<ActionDetail | null>(null)
    const [deletingAction, setDeletingAction] = useState<ActionInfo | null>(null)

    useEffect(() => {
        setIsHydrated(true)
    }, [])

    useEffect(() => {
        if (isHydrated && !token) {
            router.push('/')
        }
    }, [isHydrated, token, router])

    // Load rules
    const loadRules = useCallback(async () => {
        setRulesLoading(true)
        try {
            const res = await rulesApi.list()
            setRules(res.data.rules)
        } catch (err) {
            console.error('Failed to load rules:', err)
            toast.error(t('loadRulesFailed'))
        } finally {
            setRulesLoading(false)
        }
    }, [t])

    // Load actions
    const loadActions = useCallback(async () => {
        setActionsLoading(true)
        try {
            const res = await actionsApi.list()
            setActions(res.data.actions)
        } catch (err) {
            console.error('Failed to load actions:', err)
            toast.error(t('loadActionsFailed'))
        } finally {
            setActionsLoading(false)
        }
    }, [t])

    // Initial load
    useEffect(() => {
        if (isHydrated && token) {
            loadRules()
            loadActions()
        }
    }, [isHydrated, token, loadRules, loadActions])

    // Edit rule
    const handleEditRule = async (rule: RuleInfo) => {
        try {
            const res = await rulesApi.get(rule.name)
            setEditingRule(res.data)
            setRuleEditorOpen(true)
        } catch (err) {
            toast.error(t('loadRuleDetailFailed'))
        }
    }

    // Delete rule
    const handleDeleteRule = async () => {
        if (!deletingRule) return
        try {
            await rulesApi.delete(deletingRule.name)
            toast.success(t('ruleDeleted'))
            loadRules()
        } catch (err) {
            toast.error(t('deleteRuleFailed'))
        } finally {
            setDeletingRule(null)
        }
    }

    // Edit action
    const handleEditAction = async (action: ActionInfo) => {
        try {
            const res = await actionsApi.get(action.name)
            setEditingAction(res.data)
            setActionEditorOpen(true)
        } catch (err) {
            toast.error(t('loadActionDetailFailed'))
        }
    }

    // Delete action
    const handleDeleteAction = async () => {
        if (!deletingAction) return
        try {
            await actionsApi.delete(deletingAction.name)
            toast.success(t('actionDeleted'))
            loadActions()
        } catch (err) {
            toast.error(t('deleteActionFailed'))
        } finally {
            setDeletingAction(null)
        }
    }

    if (!isHydrated || !token) {
        return null
    }

    return (
        <AppLayout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
                            <Settings className="h-6 w-6 text-indigo-600" />
                            {t('title')}
                        </h1>
                        <p className="text-slate-600 mt-1">
                            {t('description')}
                        </p>
                    </div>
                </div>

                {/* Tabs */}
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                    <div className="flex items-center justify-between">
                        <TabsList className="bg-slate-100">
                            <TabsTrigger
                                value="rules"
                                className="data-[state=active]:bg-white"
                            >
                                <Zap className="h-4 w-4 mr-2" />
                                {t('rules')} ({rules.length})
                            </TabsTrigger>
                            <TabsTrigger
                                value="actions"
                                className="data-[state=active]:bg-white"
                            >
                                <Play className="h-4 w-4 mr-2" />
                                {t('actions')} ({actions.length})
                            </TabsTrigger>
                        </TabsList>

                        {activeTab === 'rules' ? (
                            <Button
                                onClick={() => {
                                    setEditingRule(null)
                                    setRuleEditorOpen(true)
                                }}
                                className="bg-indigo-600 hover:bg-indigo-700"
                            >
                                <Plus className="h-4 w-4 mr-2" />
                                {t('createRule')}
                            </Button>
                        ) : (
                            <Button
                                onClick={() => {
                                    setEditingAction(null)
                                    setActionEditorOpen(true)
                                }}
                                className="bg-emerald-600 hover:bg-emerald-700"
                            >
                                <Plus className="h-4 w-4 mr-2" />
                                {t('createAction')}
                            </Button>
                        )}
                    </div>

                    {/* Rules Tab */}
                    <TabsContent value="rules" className="mt-6">
                        {rulesLoading ? (
                            <div className="flex items-center justify-center py-12">
                                <RefreshCw className="h-8 w-8 animate-spin text-indigo-600" />
                            </div>
                        ) : rules.length === 0 ? (
                            <Card className="border-dashed">
                                <CardContent className="flex flex-col items-center justify-center py-12">
                                    <Layers className="h-12 w-12 text-slate-300 mb-4" />
                                    <h3 className="text-lg font-medium text-slate-600">
                                        {t('noRules')}
                                    </h3>
                                    <p className="text-slate-500 mt-1">
                                        {t('noRulesDesc')}
                                    </p>
                                </CardContent>
                            </Card>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {rules.map((rule) => (
                                    <RuleCard
                                        key={rule.id}
                                        rule={rule}
                                        onEdit={() => handleEditRule(rule)}
                                        onDelete={() => setDeletingRule(rule)}
                                    />
                                ))}
                            </div>
                        )}
                    </TabsContent>

                    {/* Actions Tab */}
                    <TabsContent value="actions" className="mt-6">
                        {actionsLoading ? (
                            <div className="flex items-center justify-center py-12">
                                <RefreshCw className="h-8 w-8 animate-spin text-emerald-600" />
                            </div>
                        ) : actions.length === 0 ? (
                            <Card className="border-dashed">
                                <CardContent className="flex flex-col items-center justify-center py-12">
                                    <Code className="h-12 w-12 text-slate-300 mb-4" />
                                    <h3 className="text-lg font-medium text-slate-600">
                                        {t('noActions')}
                                    </h3>
                                    <p className="text-slate-500 mt-1">
                                        {t('noActionsDesc')}
                                    </p>
                                </CardContent>
                            </Card>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {actions.map((action) => (
                                    <ActionCard
                                        key={action.id}
                                        action={action}
                                        onEdit={() => handleEditAction(action)}
                                        onDelete={() => setDeletingAction(action)}
                                    />
                                ))}
                            </div>
                        )}
                    </TabsContent>
                </Tabs>
            </div>

            {/* Rule Editor Dialog */}
            <RuleEditorDialog
                open={ruleEditorOpen}
                onClose={() => setRuleEditorOpen(false)}
                rule={editingRule}
                onSave={loadRules}
            />

            {/* Action Editor Dialog */}
            <ActionEditorDialog
                open={actionEditorOpen}
                onClose={() => setActionEditorOpen(false)}
                action={editingAction}
                onSave={loadActions}
            />

            {/* Delete Rule Confirmation */}
            <DeleteConfirmDialog
                open={!!deletingRule}
                onClose={() => setDeletingRule(null)}
                onConfirm={handleDeleteRule}
                itemName={deletingRule?.name || ''}
                itemType="rule"
            />

            {/* Delete Action Confirmation */}
            <DeleteConfirmDialog
                open={!!deletingAction}
                onClose={() => setDeletingAction(null)}
                onConfirm={handleDeleteAction}
                itemName={deletingAction?.name || ''}
                itemType="action"
            />
        </AppLayout>
    )
}
