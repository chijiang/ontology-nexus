"use client";

import * as React from "react";
import { useRef } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { CronTemplateSelector, type CronTemplate } from "@/components/scheduler";
import { scheduledTasksApi, type ScheduledTask, type TaskExecution } from "@/lib/api/scheduled-tasks";
import { Play, Clock, CheckCircle2, XCircle, Loader2, AlertTriangle } from "lucide-react";

interface GenericSyncSchedulePanelProps {
    targetId: number;
    targetName: string;
    targetType: "product" | "mapping";
    showCard?: boolean;
}

export function GenericSyncSchedulePanel({
    targetId,
    targetName,
    targetType,
    showCard = true
}: GenericSyncSchedulePanelProps) {
    const t = useTranslations("scheduler.panel");
    const isMountedRef = useRef(true);

    const [schedule, setSchedule] = React.useState<ScheduledTask | null>(null);
    const [cronTemplate, setCronTemplate] = React.useState<CronTemplate>({
        type: "interval",
        interval_value: 1,
        interval_unit: "hour",
    });
    const [isLoading, setIsLoading] = React.useState(true);
    const [isSaving, setIsSaving] = React.useState(false);
    const [isDeleting, setIsDeleting] = React.useState(false);
    const [isTriggering, setIsTriggering] = React.useState(false);
    const [history, setHistory] = React.useState<TaskExecution[]>([]);
    const [isLoadingHistory, setIsLoadingHistory] = React.useState(false);

    const loadSchedule = React.useCallback(async () => {
        try {
            const response = targetType === "product"
                ? await scheduledTasksApi.getProductSyncSchedule(targetId)
                : await scheduledTasksApi.getMappingSyncSchedule(targetId);

            if (isMountedRef.current) {
                const data = response.data;
                setSchedule(data);
                if (data) {
                    setCronTemplate({
                        type: "advanced",
                        advanced: data.cron_expression,
                    });
                }
            }
        } catch (error) {
            console.error("Failed to load schedule:", error);
        } finally {
            if (isMountedRef.current) {
                setIsLoading(false);
            }
        }
    }, [targetId, targetType]);

    const loadHistory = React.useCallback(async () => {
        setIsLoadingHistory(true);
        try {
            const response = targetType === "product"
                ? await scheduledTasksApi.getProductSyncHistory(targetId, 10)
                : await scheduledTasksApi.getMappingSyncHistory(targetId, 10);

            if (isMountedRef.current) {
                setHistory(response.data);
            }
        } catch (error) {
            console.error("Failed to load history:", error);
        } finally {
            if (isMountedRef.current) {
                setIsLoadingHistory(false);
            }
        }
    }, [targetId, targetType]);

    React.useEffect(() => {
        isMountedRef.current = true;
        loadSchedule();
        loadHistory();

        return () => {
            isMountedRef.current = false;
        };
    }, [loadSchedule, loadHistory]);

    const handleSave = async () => {
        setIsSaving(true);
        try {
            if (targetType === "product") {
                await scheduledTasksApi.setProductSyncSchedule(targetId, cronTemplate);
            } else {
                await scheduledTasksApi.setMappingSyncSchedule(targetId, cronTemplate);
            }
            await loadSchedule();
            toast.success(t("messages.saveSuccess"));
        } catch (error: any) {
            toast.error(error.response?.data?.detail || t("messages.saveFailed"));
        } finally {
            if (isMountedRef.current) {
                setIsSaving(false);
            }
        }
    };

    const handleDelete = async () => {
        if (!confirm(t("deleteConfirm"))) return;

        setIsDeleting(true);
        try {
            if (targetType === "product") {
                await scheduledTasksApi.deleteProductSyncSchedule(targetId);
            } else {
                await scheduledTasksApi.deleteMappingSyncSchedule(targetId);
            }
            await loadSchedule();
            toast.success(t("messages.deleteSuccess"));
        } catch (error: any) {
            toast.error(error.response?.data?.detail || t("messages.deleteFailed"));
        } finally {
            if (isMountedRef.current) {
                setIsDeleting(false);
            }
        }
    };

    const handleTrigger = async () => {
        if (!schedule) return;

        setIsTriggering(true);
        try {
            await scheduledTasksApi.triggerSync(schedule.id);
            toast.success(t("messages.triggerSuccess"));
            await loadHistory();
        } catch (error: any) {
            toast.error(error.response?.data?.detail || t("messages.triggerFailed"));
        } finally {
            if (isMountedRef.current) {
                setIsTriggering(false);
            }
        }
    };

    const getStatusIcon = (status: TaskExecution["status"]) => {
        switch (status) {
            case "pending":
                return <Clock className="h-4 w-4 text-muted-foreground" />;
            case "running":
                return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
            case "completed":
                return <CheckCircle2 className="h-4 w-4 text-green-500" />;
            case "failed":
                return <XCircle className="h-4 w-4 text-destructive" />;
            case "timeout":
                return <AlertTriangle className="h-4 w-4 text-orange-500" />;
        }
    };

    const formatDateTime = (dateStr: string) => {
        return new Date(dateStr).toLocaleString();
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-6">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
        );
    }

    const content = (
        <div className="space-y-4">
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <div className="flex-1">
                        <h4 className="text-sm font-medium">{t("title")}</h4>
                        <p className="text-xs text-muted-foreground">
                            {t("description", { name: targetName })}
                        </p>
                    </div>
                    {schedule && (
                        <div className="flex items-center gap-2">
                            <Badge variant={schedule.is_enabled ? "default" : "secondary"}>
                                {schedule.is_enabled ? t("statusEnabled") : t("statusDisabled")}
                            </Badge>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={handleTrigger}
                                disabled={isTriggering || !schedule.is_enabled}
                            >
                                {isTriggering ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                    <Play className="h-4 w-4" />
                                )}
                                {t("triggerNow")}
                            </Button>
                        </div>
                    )}
                </div>

                <div className="space-y-3">
                    <CronTemplateSelector
                        value={cronTemplate}
                        onChange={setCronTemplate}
                        disabled={isSaving}
                    />
                </div>

                {schedule && (
                    <div className="text-[10px] text-muted-foreground font-mono bg-muted/30 p-2 rounded border border-dashed text-center">
                        Cron: <span className="font-semibold">{schedule.cron_expression}</span>
                    </div>
                )}

                <div className="flex gap-2">
                    <Button size="sm" onClick={handleSave} disabled={isSaving} className="flex-1 h-8 text-xs">
                        {isSaving && <Loader2 className="h-3 w-3 mr-2 animate-spin" />}
                        {schedule ? t("update") : t("enableSync")}
                    </Button>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleDelete}
                        disabled={isDeleting}
                        className="h-8 text-xs text-destructive hover:text-destructive hover:bg-destructive/5"
                    >
                        {isDeleting && <Loader2 className="h-3 w-3 mr-2 animate-spin" />}
                        {t("delete")}
                    </Button>
                </div>
            </div>

            <div className="pt-4 border-t border-slate-100">
                <h4 className="text-xs font-semibold mb-2">{t("historyTitle")}</h4>
                {isLoadingHistory ? (
                    <div className="flex items-center justify-center py-4">
                        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    </div>
                ) : history.length === 0 ? (
                    <p className="text-[10px] text-muted-foreground text-center py-4 italic">{t("noHistory")}</p>
                ) : (
                    <div className="max-h-[200px] overflow-y-auto rounded border border-slate-100">
                        <Table>
                            <TableHeader className="bg-slate-50 sticky top-0 z-10">
                                <TableRow className="h-8">
                                    <TableHead className="text-[10px] h-8">{t("table.status")}</TableHead>
                                    <TableHead className="text-[10px] h-8">{t("table.started")}</TableHead>
                                    <TableHead className="text-[10px] h-8">{t("table.duration")}</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {history.map((execution) => (
                                    <TableRow key={execution.id} className="h-8">
                                        <TableCell className="py-1 px-2">
                                            <div className="flex items-center gap-1.5 min-w-0">
                                                {getStatusIcon(execution.status)}
                                                <span className="capitalize text-[10px] truncate">{execution.status}</span>
                                            </div>
                                        </TableCell>
                                        <TableCell className="py-1 px-2 text-[10px] whitespace-nowrap">
                                            {new Date(execution.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </TableCell>
                                        <TableCell className="py-1 px-2 text-[10px]">
                                            {execution.duration_seconds
                                                ? `${Math.round(execution.duration_seconds)}s`
                                                : "-"}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                )}
            </div>
        </div>
    );

    if (!showCard) return content;

    return (
        <Card className="border-slate-200 shadow-none">
            <CardHeader className="pb-3">
                <CardTitle className="text-sm">{t("syncTitle", { defaultValue: "Synchronization" })}</CardTitle>
                <CardDescription className="text-xs">
                    {t("syncDesc", { defaultValue: `Automatic sync for this ${targetType === "product" ? "product" : "mapping"}` })}
                </CardDescription>
            </CardHeader>
            <CardContent>{content}</CardContent>
        </Card>
    );
}
