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

interface SyncSchedulePanelProps {
  productId: number;
  productName: string;
}

export function SyncSchedulePanel({ productId, productName }: SyncSchedulePanelProps) {
  const t = useTranslations();
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
      const response = await scheduledTasksApi.getProductSyncSchedule(productId);
      if (isMountedRef.current) {
        const data = response.data;
        setSchedule(data);
        if (data) {
          // Parse cron expression to template (simplified - backend handles conversion)
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
  }, [productId]);

  const loadHistory = React.useCallback(async () => {
    setIsLoadingHistory(true);
    try {
      const response = await scheduledTasksApi.getProductSyncHistory(productId, 10);
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
  }, [productId]);

  React.useEffect(() => {
    loadSchedule();
    loadHistory();
  }, [loadSchedule, loadHistory]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await scheduledTasksApi.setProductSyncSchedule(productId, cronTemplate);
      await loadSchedule();
      toast.success("Sync schedule saved successfully");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to save sync schedule");
    } finally {
      if (isMountedRef.current) {
        setIsSaving(false);
      }
    }
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete the sync schedule?")) return;

    setIsDeleting(true);
    try {
      await scheduledTasksApi.deleteProductSyncSchedule(productId);
      await loadSchedule();
      toast.success("Sync schedule deleted");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to delete sync schedule");
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
      toast.success("Sync triggered successfully");
      await loadHistory();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to trigger sync");
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
              <CardTitle>Sync Schedule</CardTitle>
              <CardDescription>
                Configure automatic synchronization for "{productName}"
              </CardDescription>
            </div>
            {schedule && (
              <div className="flex items-center gap-2">
                <Badge variant={schedule.is_enabled ? "default" : "secondary"}>
                  {schedule.is_enabled ? "Enabled" : "Disabled"}
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
                  Trigger Now
                </Button>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {schedule && (
            <div className="flex items-center justify-between rounded-lg border p-3 bg-muted/50">
              <Label htmlFor="enable-schedule" className="cursor-pointer">
                Enable scheduled sync
              </Label>
              <Switch
                id="enable-schedule"
                checked={schedule.is_enabled}
                disabled={isSaving}
                onCheckedChange={async (checked) => {
                  // Update via save with current template
                  await handleSave();
                }}
              />
            </div>
          )}

          <div className="space-y-3">
            <Label>Schedule Configuration</Label>
            <CronTemplateSelector
              value={cronTemplate}
              onChange={setCronTemplate}
              disabled={isSaving}
            />
          </div>

          {schedule && (
            <div className="text-xs text-muted-foreground">
              <p>Cron expression: <code className="bg-muted px-1.5 py-0.5 rounded">{schedule.cron_expression}</code></p>
              <p className="mt-1">Last updated: {formatDateTime(schedule.updated_at)}</p>
            </div>
          )}

          <div className="flex gap-2 pt-2">
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {schedule ? "Update Schedule" : "Create Schedule"}
            </Button>
            {schedule && (
              <Button
                variant="destructive"
                onClick={handleDelete}
                disabled={isDeleting}
              >
                {isDeleting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Delete Schedule
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Sync History</CardTitle>
          <CardDescription>Recent synchronization executions</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoadingHistory ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : history.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-6">No sync history yet</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Status</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Retry</TableHead>
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
                    <TableCell>{execution.retry_count}</TableCell>
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
