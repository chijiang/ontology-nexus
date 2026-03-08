"use client";

import * as React from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useTranslations } from "next-intl";
import type { CronTemplate, CronTemplateSelectorProps, IntervalUnit, Frequency, IntervalTemplate, SpecificTemplate } from "./CronTemplateSelector.types";

export function CronTemplateSelector({
  value,
  onChange,
  disabled = false,
  error,
}: CronTemplateSelectorProps) {
  const t = useTranslations("scheduler");
  const [activeTab, setActiveTab] = React.useState<CronTemplate["type"]>(value.type);

  const handleTabChange = (newType: CronTemplate["type"]) => {
    setActiveTab(newType);
    // Initialize default value for the new type
    switch (newType) {
      case "interval":
        onChange({ type: "interval", interval_value: 1, interval_unit: "hour" });
        break;
      case "specific":
        onChange({ type: "specific", frequency: "daily" });
        break;
      case "advanced":
        onChange({ type: "advanced", advanced: "0 * * * *" });
        break;
    }
  };

  const handleIntervalChange = (field: keyof IntervalTemplate, val: any) => {
    if (value.type !== "interval") return;
    onChange({ ...value, [field]: val });
  };

  const handleSpecificChange = (field: keyof SpecificTemplate, val: any) => {
    if (value.type !== "specific") return;
    onChange({ ...value, [field]: val });
  };

  const handleAdvancedChange = (val: string) => {
    if (value.type !== "advanced") return;
    onChange({ ...value, advanced: val });
  };

  return (
    <div className="space-y-3">
      <Tabs value={activeTab} onValueChange={(v) => handleTabChange(v as CronTemplate["type"])}>
        <TabsList>
          <TabsTrigger value="interval">{t("tabs.interval")}</TabsTrigger>
          <TabsTrigger value="specific">{t("tabs.specific")}</TabsTrigger>
          <TabsTrigger value="advanced">{t("tabs.advanced")}</TabsTrigger>
        </TabsList>

        <TabsContent value="interval" className="space-y-4 mt-4">
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <Label htmlFor="interval-value">{t("interval.every")}</Label>
              <Input
                id="interval-value"
                type="number"
                min="1"
                value={value.type === "interval" ? value.interval_value : 1}
                onChange={(e) => handleIntervalChange("interval_value", parseInt(e.target.value) || 1)}
                disabled={disabled}
                className="mt-1.5"
              />
            </div>
            <div className="w-[140px]">
              <Label htmlFor="interval-unit">{t("interval.unit")}</Label>
              <Select
                value={value.type === "interval" ? value.interval_unit : "hour"}
                onValueChange={(v) => handleIntervalChange("interval_unit", v as IntervalUnit)}
                disabled={disabled}
              >
                <SelectTrigger id="interval-unit" className="mt-1.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="second">{t("interval.second")}</SelectItem>
                  <SelectItem value="minute">{t("interval.minute")}</SelectItem>
                  <SelectItem value="hour">{t("interval.hour")}</SelectItem>
                  <SelectItem value="day">{t("interval.day")}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            {value.type === "interval" && (
              t("interval.summary", {
                value: value.interval_value,
                unit: t(`interval.${value.interval_unit}`),
                plural: value.interval_value > 1 ? "s" : ""
              })
            )}
          </p>
        </TabsContent>

        <TabsContent value="specific" className="space-y-4 mt-4">
          <div>
            <Label htmlFor="frequency">{t("specific.frequency")}</Label>
            <Select
              value={value.type === "specific" ? value.frequency : "daily"}
              onValueChange={(v) => {
                const freq = v as Frequency;
                handleSpecificChange("frequency", freq);

                // Use a functional update style if needed, but here we just send the new object
                const nextValue: CronTemplate = {
                  type: "specific",
                  frequency: freq,
                  time: freq === "hourly" ? undefined : (value.type === "specific" ? value.time : "00:00"),
                  day_of_week: freq === "weekly" ? (value.type === "specific" ? value.day_of_week : 1) : undefined,
                  day_of_month: freq === "monthly" ? (value.type === "specific" ? value.day_of_month : 1) : undefined,
                };
                onChange(nextValue);
              }}
              disabled={disabled}
            >
              <SelectTrigger id="frequency" className="mt-1.5">
                <SelectValue placeholder={t("specific.frequency")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="hourly">{t("specific.hourly")}</SelectItem>
                <SelectItem value="daily">{t("specific.daily")}</SelectItem>
                <SelectItem value="weekly">{t("specific.weekly")}</SelectItem>
                <SelectItem value="monthly">{t("specific.monthly")}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {value.type === "specific" && value.frequency !== "hourly" && (
            <div>
              <Label htmlFor="specific-time">{t("specific.atTime")}</Label>
              <Input
                id="specific-time"
                type="time"
                value={value.time || "00:00"}
                onChange={(e) => handleSpecificChange("time", e.target.value)}
                disabled={disabled}
                className="mt-1.5 w-[180px]"
              />
            </div>
          )}

          {value.type === "specific" && value.frequency === "weekly" && (
            <div>
              <Label htmlFor="day-of-week">{t("specific.dayOfWeek")}</Label>
              <Select
                value={value.day_of_week?.toString() || "1"}
                onValueChange={(v) => handleSpecificChange("day_of_week", parseInt(v))}
                disabled={disabled}
              >
                <SelectTrigger id="day-of-week" className="mt-1.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">{t("days.1")}</SelectItem>
                  <SelectItem value="2">{t("days.2")}</SelectItem>
                  <SelectItem value="3">{t("days.3")}</SelectItem>
                  <SelectItem value="4">{t("days.4")}</SelectItem>
                  <SelectItem value="5">{t("days.5")}</SelectItem>
                  <SelectItem value="6">{t("days.6")}</SelectItem>
                  <SelectItem value="0">{t("days.0")}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          {value.type === "specific" && value.frequency === "monthly" && (
            <div>
              <Label htmlFor="day-of-month">{t("specific.dayOfMonth")}</Label>
              <Input
                id="day-of-month"
                type="number"
                min="1"
                max="31"
                value={value.day_of_month || 1}
                onChange={(e) => handleSpecificChange("day_of_month", Math.min(31, Math.max(1, parseInt(e.target.value) || 1)))}
                disabled={disabled}
                className="mt-1.5 w-[120px]"
              />
            </div>
          )}

          {value.type === "specific" && (
            <p className="text-xs text-muted-foreground">
              {value.frequency === "hourly" && t("specific.summaryHourly")}
              {value.frequency === "daily" && t("specific.summaryDaily", { time: value.time || "00:00" })}
              {value.frequency === "weekly" && t("specific.summaryWeekly", { day: t(`days.${value.day_of_week ?? 1}`), time: value.time || "00:00" })}
              {value.frequency === "monthly" && t("specific.summaryMonthly", { day: value.day_of_month ?? 1, time: value.time || "00:00" })}
            </p>
          )}
        </TabsContent>

        <TabsContent value="advanced" className="space-y-4 mt-4">
          <div>
            <Label htmlFor="cron-expr">{t("advanced.cronExpression")}</Label>
            <Input
              id="cron-expr"
              value={value.type === "advanced" ? value.advanced : ""}
              onChange={(e) => handleAdvancedChange(e.target.value)}
              disabled={disabled}
              placeholder={t("advanced.placeholder")}
              className="mt-1.5 font-mono"
            />
            <p className="text-xs text-muted-foreground mt-1.5">
              {t("advanced.help")}
            </p>
          </div>
        </TabsContent>
      </Tabs>

      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}
    </div>
  );
}
