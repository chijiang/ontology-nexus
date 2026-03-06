export type CronTemplateType = 'interval' | 'specific' | 'advanced';
export type IntervalUnit = 'second' | 'minute' | 'hour' | 'day';
export type Frequency = 'hourly' | 'daily' | 'weekly' | 'monthly';

export interface IntervalTemplate {
  type: 'interval';
  interval_value: number;
  interval_unit: IntervalUnit;
}

export interface SpecificTemplate {
  type: 'specific';
  frequency: Frequency;
  time?: string;
  day_of_week?: number;
  day_of_month?: number;
}

export interface AdvancedTemplate {
  type: 'advanced';
  advanced: string;
}

export type CronTemplate = IntervalTemplate | SpecificTemplate | AdvancedTemplate;

export interface CronTemplateSelectorProps {
  value: CronTemplate;
  onChange: (value: CronTemplate) => void;
  disabled?: boolean;
  error?: string;
}
