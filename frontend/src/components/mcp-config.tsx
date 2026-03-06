// frontend/src/components/mcp-config.tsx
// Trigger re-save to fix module resolution
'use client'

import { useState, useEffect } from 'react'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { mcpApi, MCPConfig } from '@/lib/api'
import { toast } from 'sonner'
import { Plus, Trash2, Power, PowerOff, Loader2 } from 'lucide-react'
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table'
import { Switch } from '@/components/ui/switch'

export function MCPConfigManager() {
    const t = useTranslations()
    const [servers, setServers] = useState<MCPConfig[]>([])
    const [loading, setLoading] = useState(true)
    const [adding, setAdding] = useState(false)
    const [newServer, setNewServer] = useState({ name: '', url: '' })

    useEffect(() => {
        loadServers()
    }, [])

    const loadServers = async () => {
        setLoading(true)
        try {
            const res = await mcpApi.list()
            setServers(res.data)
        } catch (err) {
            toast.error(t('dataProducts.loadFailed'))
        } finally {
            setLoading(false)
        }
    }

    const handleRegister = async () => {
        if (!newServer.name || !newServer.url) {
            toast.error(t('dataProducts.fillRequired'))
            return
        }

        setAdding(true)
        try {
            await mcpApi.create({ ...newServer, mcp_type: 'sse' })
            toast.success(t('config.registerMcpSuccess'))
            setNewServer({ name: '', url: '' })
            loadServers()
        } catch (err: any) {
            toast.error(err.response?.data?.detail || t('common.error'))
        } finally {
            setAdding(false)
        }
    }

    const handleToggleActive = async (server: MCPConfig) => {
        try {
            await mcpApi.update(server.id, { is_active: !server.is_active })
            loadServers()
        } catch (err) {
            toast.error(t('common.error'))
        }
    }

    const handleDelete = async (id: number) => {
        if (!confirm(t('config.deleteMcpConfirm'))) return
        try {
            await mcpApi.delete(id)
            toast.success(t('config.deleteMcpSuccess'))
            loadServers()
        } catch (err) {
            toast.error(t('common.error'))
        }
    }

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle>{t('config.registerMcp')}</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Input
                            placeholder={t('config.mcpName')}
                            value={newServer.name}
                            onChange={(e) => setNewServer({ ...newServer, name: e.target.value })}
                        />
                        <Input
                            placeholder={t('config.mcpUrl')}
                            value={newServer.url}
                            onChange={(e) => setNewServer({ ...newServer, url: e.target.value })}
                        />
                    </div>
                    <Button className="mt-4" onClick={handleRegister} disabled={adding}>
                        {adding ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Plus className="mr-2 h-4 w-4" />}
                        {t('common.add')}
                    </Button>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle>{t('config.mcpManagement')}</CardTitle>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="flex justify-center p-8">
                            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                        </div>
                    ) : servers.length === 0 ? (
                        <div className="text-center p-8 text-muted-foreground">
                            {t('dataProducts.noProducts')}
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>{t('config.mcpName')}</TableHead>
                                    <TableHead>{t('config.mcpUrl')}</TableHead>
                                    <TableHead className="w-[100px]">{t('config.status')}</TableHead>
                                    <TableHead className="w-[100px] text-right">{t('config.actions')}</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {servers.map((server) => (
                                    <TableRow key={server.id}>
                                        <TableCell className="font-medium">{server.name}</TableCell>
                                        <TableCell className="text-muted-foreground truncate max-w-[300px]">{server.url}</TableCell>
                                        <TableCell>
                                            <Switch
                                                checked={server.is_active}
                                                onCheckedChange={() => handleToggleActive(server)}
                                            />
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                onClick={() => handleDelete(server.id)}
                                                className="text-destructive hover:text-destructive hover:bg-destructive/10"
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>
        </div>
    )
}
