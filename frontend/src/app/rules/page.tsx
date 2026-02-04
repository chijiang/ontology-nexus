'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
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
} from 'lucide-react'

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
                                优先级: {rule.priority}
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={onEdit}
                            className="h-8 w-8 p-0 text-slate-500 hover:text-indigo-600"
                        >
                            <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={onDelete}
                            className="h-8 w-8 p-0 text-slate-500 hover:text-red-600"
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
                            激活
                        </span>
                    ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                            <XCircle className="h-3 w-3 mr-1" />
                            禁用
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
                                实体类型: {action.entity_type}
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={onEdit}
                            className="h-8 w-8 p-0 text-slate-500 hover:text-emerald-600"
                        >
                            <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={onDelete}
                            className="h-8 w-8 p-0 text-slate-500 hover:text-red-600"
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
                            激活
                        </span>
                    ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                            <XCircle className="h-3 w-3 mr-1" />
                            禁用
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
    const [name, setName] = useState('')
    const [priority, setPriority] = useState(0)
    const [isActive, setIsActive] = useState(true)
    const [dslContent, setDslContent] = useState('')
    const [error, setError] = useState('')
    const [saving, setSaving] = useState(false)

    useEffect(() => {
        if (rule) {
            setName(rule.name)
            setPriority(rule.priority)
            setIsActive(rule.is_active)
            setDslContent(rule.dsl_content)
        } else {
            setName('')
            setPriority(100)
            setIsActive(true)
            setDslContent(`// 新规则示例
RULE NewRule PRIORITY 100 {
    ON UPDATE(Entity.property)
    FOR (e: Entity WHERE e.status == "Active") {
        SET e.processedAt = NOW();
    }
}
`)
        }
        setError('')
    }, [rule, open])

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
                toast.success('规则更新成功')
            } else {
                // Create new rule
                if (!name.trim()) {
                    setError('请输入规则名称')
                    setSaving(false)
                    return
                }
                await rulesApi.create({
                    name: name.trim(),
                    dsl_content: dslContent,
                    priority,
                    is_active: isActive,
                })
                toast.success('规则创建成功')
            }
            onSave()
            onClose()
        } catch (err: any) {
            const message = err.response?.data?.detail || '操作失败'
            setError(message)
            toast.error(message)
        } finally {
            setSaving(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Zap className="h-5 w-5 text-indigo-600" />
                        {rule ? '编辑规则' : '创建规则'}
                    </DialogTitle>
                    <DialogDescription>
                        使用 DSL 语法定义规则。规则会在触发条件满足时自动执行。
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-slate-700">
                                规则名称
                            </label>
                            <Input
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="例如: SupplierStatusBlocking"
                                disabled={!!rule}
                                className={rule ? 'bg-slate-100' : ''}
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-slate-700">
                                优先级
                            </label>
                            <Input
                                type="number"
                                value={priority}
                                onChange={(e) => setPriority(parseInt(e.target.value) || 0)}
                                placeholder="100"
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
                            激活规则
                        </label>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-700">
                            DSL 内容
                        </label>
                        <DslEditor
                            value={dslContent}
                            onChange={setDslContent}
                            error={error}
                            placeholder="请输入规则 DSL..."
                        />
                    </div>

                    {/* DSL Help */}
                    <div className="bg-slate-50 rounded-lg p-4 text-sm">
                        <h4 className="font-medium text-slate-700 mb-2">DSL 语法提示</h4>
                        <div className="grid grid-cols-2 gap-4 text-slate-600">
                            <div>
                                <p className="font-mono text-xs bg-white px-2 py-1 rounded mb-1">
                                    ON UPDATE(Entity.prop)
                                </p>
                                <p className="text-xs">属性更新触发器</p>
                            </div>
                            <div>
                                <p className="font-mono text-xs bg-white px-2 py-1 rounded mb-1">
                                    FOR (v: Entity WHERE condition)
                                </p>
                                <p className="text-xs">作用域定义</p>
                            </div>
                            <div>
                                <p className="font-mono text-xs bg-white px-2 py-1 rounded mb-1">
                                    SET entity.prop = value;
                                </p>
                                <p className="text-xs">设置属性值</p>
                            </div>
                            <div>
                                <p className="font-mono text-xs bg-white px-2 py-1 rounded mb-1">
                                    TRIGGER Action.name ON target;
                                </p>
                                <p className="text-xs">触发动作</p>
                            </div>
                        </div>
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={onClose} disabled={saving}>
                        取消
                    </Button>
                    <Button onClick={handleSave} disabled={saving}>
                        {saving ? (
                            <>
                                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                                保存中...
                            </>
                        ) : (
                            '保存'
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
    const [name, setName] = useState('')
    const [entityType, setEntityType] = useState('')
    const [isActive, setIsActive] = useState(true)
    const [dslContent, setDslContent] = useState('')
    const [error, setError] = useState('')
    const [saving, setSaving] = useState(false)

    useEffect(() => {
        if (action) {
            setName(action.name)
            setEntityType(action.entity_type)
            setIsActive(action.is_active)
            setDslContent(action.dsl_content)
        } else {
            setName('')
            setEntityType('')
            setIsActive(true)
            setDslContent(`// 新动作示例
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
    }, [action, open])

    const handleSave = async () => {
        setError('')
        setSaving(true)

        try {
            if (action) {
                // Update existing action
                await actionsApi.update(action.name, {
                    dsl_content: dslContent,
                    is_active: isActive,
                })
                toast.success('动作更新成功')
            } else {
                // Create new action
                if (!name.trim()) {
                    setError('请输入动作名称')
                    setSaving(false)
                    return
                }
                if (!entityType.trim()) {
                    setError('请输入实体类型')
                    setSaving(false)
                    return
                }
                await actionsApi.create({
                    name: name.trim(),
                    entity_type: entityType.trim(),
                    dsl_content: dslContent,
                    is_active: isActive,
                })
                toast.success('动作创建成功')
            }
            onSave()
            onClose()
        } catch (err: any) {
            const message = err.response?.data?.detail || '操作失败'
            setError(message)
            toast.error(message)
        } finally {
            setSaving(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Play className="h-5 w-5 text-emerald-600" />
                        {action ? '编辑动作' : '创建动作'}
                    </DialogTitle>
                    <DialogDescription>
                        使用 DSL 语法定义动作。动作定义了实体可执行的操作及其前置条件。
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-slate-700">
                                动作名称
                            </label>
                            <Input
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="例如: PurchaseOrder.submit"
                                disabled={!!action}
                                className={action ? 'bg-slate-100' : ''}
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-slate-700">
                                实体类型
                            </label>
                            <Input
                                value={entityType}
                                onChange={(e) => setEntityType(e.target.value)}
                                placeholder="例如: PurchaseOrder"
                                disabled={!!action}
                                className={action ? 'bg-slate-100' : ''}
                            />
                        </div>
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
                            激活动作
                        </label>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-700">
                            DSL 内容
                        </label>
                        <DslEditor
                            value={dslContent}
                            onChange={setDslContent}
                            error={error}
                            placeholder="请输入动作 DSL..."
                        />
                    </div>

                    {/* DSL Help */}
                    <div className="bg-slate-50 rounded-lg p-4 text-sm">
                        <h4 className="font-medium text-slate-700 mb-2">DSL 语法提示</h4>
                        <div className="grid grid-cols-2 gap-4 text-slate-600">
                            <div>
                                <p className="font-mono text-xs bg-white px-2 py-1 rounded mb-1">
                                    PRECONDITION name: condition
                                </p>
                                <p className="text-xs">前置条件检查</p>
                            </div>
                            <div>
                                <p className="font-mono text-xs bg-white px-2 py-1 rounded mb-1">
                                    ON_FAILURE: "message"
                                </p>
                                <p className="text-xs">条件失败时的错误消息</p>
                            </div>
                            <div>
                                <p className="font-mono text-xs bg-white px-2 py-1 rounded mb-1">
                                    EFFECT {'{'} ... {'}'}
                                </p>
                                <p className="text-xs">动作执行效果</p>
                            </div>
                            <div>
                                <p className="font-mono text-xs bg-white px-2 py-1 rounded mb-1">
                                    SET this.prop = value;
                                </p>
                                <p className="text-xs">设置实体属性</p>
                            </div>
                        </div>
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={onClose} disabled={saving}>
                        取消
                    </Button>
                    <Button
                        onClick={handleSave}
                        disabled={saving}
                        className="bg-emerald-600 hover:bg-emerald-700"
                    >
                        {saving ? (
                            <>
                                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                                保存中...
                            </>
                        ) : (
                            '保存'
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
                        确认删除
                    </DialogTitle>
                    <DialogDescription>
                        确定要删除{itemType === 'rule' ? '规则' : '动作'} "{itemName}"
                        吗？此操作无法撤销。
                    </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                    <Button variant="outline" onClick={onClose} disabled={deleting}>
                        取消
                    </Button>
                    <Button
                        variant="destructive"
                        onClick={handleConfirm}
                        disabled={deleting}
                    >
                        {deleting ? (
                            <>
                                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                                删除中...
                            </>
                        ) : (
                            '删除'
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
            toast.error('加载规则失败')
        } finally {
            setRulesLoading(false)
        }
    }, [])

    // Load actions
    const loadActions = useCallback(async () => {
        setActionsLoading(true)
        try {
            const res = await actionsApi.list()
            setActions(res.data.actions)
        } catch (err) {
            console.error('Failed to load actions:', err)
            toast.error('加载动作失败')
        } finally {
            setActionsLoading(false)
        }
    }, [])

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
            toast.error('加载规则详情失败')
        }
    }

    // Delete rule
    const handleDeleteRule = async () => {
        if (!deletingRule) return
        try {
            await rulesApi.delete(deletingRule.name)
            toast.success('规则删除成功')
            loadRules()
        } catch (err) {
            toast.error('删除规则失败')
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
            toast.error('加载动作详情失败')
        }
    }

    // Delete action
    const handleDeleteAction = async () => {
        if (!deletingAction) return
        try {
            await actionsApi.delete(deletingAction.name)
            toast.success('动作删除成功')
            loadActions()
        } catch (err) {
            toast.error('删除动作失败')
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
                            业务逻辑管理器
                        </h1>
                        <p className="text-slate-600 mt-1">
                            管理知识图谱的业务规则和可执行动作
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
                                规则 ({rules.length})
                            </TabsTrigger>
                            <TabsTrigger
                                value="actions"
                                className="data-[state=active]:bg-white"
                            >
                                <Play className="h-4 w-4 mr-2" />
                                动作 ({actions.length})
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
                                创建规则
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
                                创建动作
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
                                        暂无规则
                                    </h3>
                                    <p className="text-slate-500 mt-1">
                                        点击"创建规则"按钮添加第一个规则
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
                                        暂无动作
                                    </h3>
                                    <p className="text-slate-500 mt-1">
                                        点击"创建动作"按钮添加第一个动作
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
