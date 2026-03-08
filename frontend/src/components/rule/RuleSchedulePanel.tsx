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
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { Play, Clock, CheckCircle2, XCircle, Loader2, AlertTriangle, Calendar } from "lucide-react";

interface RuleSchedulePanelProps {
  ruleId: number;
  ruleName: string;
}

type TriggerMode = "event" | "scheduled" | "hybrid";

export function RuleSchedulePanel({ ruleId, ruleName }: RuleSchedulePanelProps) {
  const t = useTranslations("scheduler.rulePanel");
  const isMountedRef = useRef(true);

  const [schedule, setSchedule] = React.useState<ScheduledTask | null>(null);
  const [triggerMode, setTriggerMode] = React.useState<TriggerMode>("event");
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
      const response = await scheduledTasksApi.getRuleSchedule(ruleId);
      if (isMountedRef.current) {
        const data = response.data;
        setSchedule(data);
        if (data) {
          setTriggerMode("scheduled");
          setCronTemplate({
            type: "advanced",
            advanced: data.cron_expression,
          });
        } else {
          setTriggerMode("event");
        }
      }
    } catch (error) {
      console.error("Failed to load schedule:", error);
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [ruleId]);

  const loadHistory = React.useCallback(async () => {
    setIsLoadingHistory(true);
    try {
      const response = await scheduledTasksApi.getRuleExecutionHistory(ruleId, 10);
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
  }, [ruleId]);

  React.useEffect(() => {
    loadSchedule();
    loadHistory();
  }, [loadSchedule, loadHistory]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      if (triggerMode === "scheduled") {
        await scheduledTasksApi.setRuleSchedule(ruleId, cronTemplate);
      } else {
        await scheduledTasksApi.deleteRuleSchedule(ruleId);
      }
      await loadSchedule();
      toast.success(t("messages.modeUpdated", { mode: triggerMode }));
    } catch (error: any) {
      toast.error(error.response?.data?.detail || t("messages.updateFailed"));
    } finally {
      if (isMountedRef.current) {
        setIsSaving(false);
      }
    }
  };

  const handleDeleteSchedule = async () => {
    if (!confirm(t("removeConfirm"))) return;

    setIsDeleting(true);
    try {
      await scheduledTasksApi.deleteRuleSchedule(ruleId);
      setTriggerMode("event");
      await loadSchedule();
      toast.success(t("messages.removeSuccess"));
    } catch (error: any) {
      toast.error(error.response?.data?.detail || t("messages.removeFailed"));
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
      <Card>
        <CardContent className="py-6">
          <div className="flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>{t("title")}</CardTitle>
              <CardDescription>
                {t("description", { name: ruleName })}
              </CardDescription>
            </div>
            {schedule && (
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
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <Label htmlFor="trigger-mode">{t("modeLabel")}</Label>
            <Select
              value={triggerMode}
              onValueChange={(v) => setTriggerMode(v as TriggerMode)}
              disabled={isSaving}
            >
              <SelectTrigger id="trigger-mode">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="event">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4" />
                    <div>
                      <div className="font-medium">{t("modes.event")}</div>
                      <div className="text-xs text-muted-foreground">
                        {t("modes.eventDesc")}
                      </div>
                    </div>
                  </div>
                </SelectItem>
                <SelectItem value="scheduled">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    <div>
                      <div className="font-medium">{t("modes.scheduled")}</div>
                      <div className="text-xs text-muted-foreground">
                        {t("modes.scheduledDesc")}
                      </div>
                    </div>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {triggerMode === "scheduled" && (
            <>
              <div className="space-y-3">
                <Label>{t("configTitle")}</Label>
                <CronTemplateSelector
                  value={cronTemplate}
                  onChange={setCronTemplate}
                  disabled={isSaving}
                />
              </div>

              {schedule && (
                <div className="text-xs text-muted-foreground">
                  <p>{useTranslations("scheduler.advanced")("cronExpression")}: <code className="bg-muted px-1.5 py-0.5 rounded">{schedule.cron_expression}</code></p>
                  <p className="mt-1">{t("lastUpdated", { defaultValue: "Last updated" })}: {formatDateTime(schedule.updated_at)}</p>
                </div>
              )}

              <div className="flex gap-2 pt-2">
                <Button onClick={handleSave} disabled={isSaving}>
                  {isSaving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  {schedule ? t("updateSchedule") : t("createSchedule")}
                </Button>
                {schedule && (
                  <Button
                    variant="outline"
                    onClick={handleDeleteSchedule}
                    disabled={isDeleting}
                  >
                    {isDeleting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                    {t("removeSchedule")}
                  </Button>
                )}
              </div>
            </>
          )}

          {triggerMode === "event" && (
            <div className="rounded-lg border p-4 bg-muted/50">
              <p className="text-sm text-muted-foreground">
                {t("infoEvent")}
              </p>
              {schedule && (
                <Button
                  variant="outline"
                  onClick={handleDeleteSchedule}
                  disabled={isDeleting}
                  className="mt-3"
                >
                  {isDeleting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  {t("removeExisting")}
                </Button>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("historyTitle")}</CardTitle>
          <CardDescription>{t("historyDesc")}</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoadingHistory ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : history.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-6">{t("noHistory")}</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("table.status")}</TableHead>
                  <TableHead>{t("table.started")}</TableHead>
                  <TableHead>{t("table.duration")}</TableHead>
                  <TableHead>{t("table.triggeredBy")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {history.map((execution) => (
                  <TableRow key={execution.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {getStatusIcon(execution.status)}
                        <span className="capitalize">{execution.status}</span>
                        {execution.is_retry && (
                          <Badge variant="outline" className="text-xs">Retry #{execution.retry_count}</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>{formatDateTime(execution.started_at)}</TableCell>
                    <TableCell>
                      {execution.duration_seconds
                        ? `${execution.duration_seconds}s`
                        : execution.completed_at
                          ? `${Math.round((new Date(execution.completed_at).getTime() - new Date(execution.started_at).getTime()) / 1000)}s`
                          : "-"}
                    </TableCell>
                    <TableCell>
                      {execution.triggered_by || <span className="text-muted-foreground">System</span>}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
