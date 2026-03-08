import { api } from '../api';

export interface CronTemplate {
  type: 'interval' | 'specific' | 'advanced';
  interval_value?: number;
  interval_unit?: 'second' | 'minute' | 'hour' | 'day';
  frequency?: 'hourly' | 'daily' | 'weekly' | 'monthly';
  time?: string;
  day_of_week?: number;
  day_of_month?: number;
  advanced?: string;
}

export interface ScheduledTask {
  id: number;
  task_type: 'sync' | 'rule';
  task_name: string;
  target_id: number;
  cron_expression: string;
  is_enabled: boolean;
  timeout_seconds: number;
  max_retries: number;
  retry_interval_seconds: number;
  priority: number;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface TaskExecution {
  id: number;
  task_id: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'timeout';
  started_at: string;
  completed_at?: string;
  duration_seconds?: number;
  error_message?: string;
  retry_count: number;
  is_retry: boolean;
  triggered_by?: string;
}

export const scheduledTasksApi = {
  getProductSyncSchedule: (productId: number) =>
    api.get<ScheduledTask | null>(`/data-products/${productId}/sync-schedule`),

  setProductSyncSchedule: (productId: number, template: CronTemplate) =>
    api.put<ScheduledTask>(`/data-products/${productId}/sync-schedule`, template),

  deleteProductSyncSchedule: (productId: number) =>
    api.delete(`/data-products/${productId}/sync-schedule`),

  getProductSyncHistory: (productId: number, limit = 20) =>
    api.get<TaskExecution[]>(`/data-products/${productId}/sync-history?limit=${limit}`),

  triggerSync: (taskId: number) =>
    api.post(`/scheduled-tasks/${taskId}/trigger`),

  getMappingSyncSchedule: (mappingId: number) =>
    api.get<ScheduledTask | null>(`/data-products/mappings/${mappingId}/sync-schedule`),

  setMappingSyncSchedule: (mappingId: number, template: CronTemplate) =>
    api.put<ScheduledTask>(`/data-products/mappings/${mappingId}/sync-schedule`, template),

  deleteMappingSyncSchedule: (mappingId: number) =>
    api.delete(`/data-products/mappings/${mappingId}/sync-schedule`),

  getMappingSyncHistory: (mappingId: number, limit = 20) =>
    api.get<TaskExecution[]>(`/data-products/mappings/${mappingId}/sync-history?limit=${limit}`),

  getRuleSchedule: (ruleId: number) =>
    api.get<ScheduledTask | null>(`/rules/${ruleId}/schedule`),

  setRuleSchedule: (ruleId: number, template: CronTemplate) =>
    api.put<ScheduledTask>(`/rules/${ruleId}/schedule`, template),

  deleteRuleSchedule: (ruleId: number) =>
    api.delete(`/rules/${ruleId}/schedule`),

  getRuleExecutionHistory: (ruleId: number, limit = 20) =>
    api.get<TaskExecution[]>(`/rules/${ruleId}/execution-history?limit=${limit}`),
};
