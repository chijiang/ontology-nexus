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
import type { CronTemplate, CronTemplateSelectorProps, IntervalUnit, Frequency, IntervalTemplate, SpecificTemplate } from "./CronTemplateSelector.types";

export function CronTemplateSelector({
  value,
  onChange,
  disabled = false,
  error,
}: CronTemplateSelectorProps) {
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
          <TabsTrigger value="interval">Interval</TabsTrigger>
          <TabsTrigger value="specific">Specific</TabsTrigger>
          <TabsTrigger value="advanced">Advanced</TabsTrigger>
        </TabsList>

        <TabsContent value="interval" className="space-y-4 mt-4">
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <Label htmlFor="interval-value">Every</Label>
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
              <Label htmlFor="interval-unit">Unit</Label>
              <Select
                value={value.type === "interval" ? value.interval_unit : "hour"}
                onValueChange={(v) => handleIntervalChange("interval_unit", v as IntervalUnit)}
                disabled={disabled}
              >
                <SelectTrigger id="interval-unit" className="mt-1.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="second">Second(s)</SelectItem>
                  <SelectItem value="minute">Minute(s)</SelectItem>
                  <SelectItem value="hour">Hour(s)</SelectItem>
                  <SelectItem value="day">Day(s)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            {value.type === "interval" && (
              <>
                Runs every <strong>{value.interval_value} {value.interval_unit}{value.interval_value > 1 ? "s" : ""}</strong>
              </>
            )}
          </p>
        </TabsContent>

        <TabsContent value="specific" className="space-y-4 mt-4">
          <div>
            <Label htmlFor="frequency">Frequency</Label>
            <Select
              value={value.type === "specific" ? value.frequency : "daily"}
              onValueChange={(v) => {
                handleSpecificChange("frequency", v as Frequency);
                // Reset dependent fields when frequency changes
                if (v !== "weekly") handleSpecificChange("day_of_week", undefined);
                if (v !== "monthly") handleSpecificChange("day_of_month", undefined);
                if (v === "hourly") handleSpecificChange("time", undefined);
              }}
              disabled={disabled}
            >
              <SelectTrigger id="frequency" className="mt-1.5">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="hourly">Hourly</SelectItem>
                <SelectItem value="daily">Daily</SelectItem>
                <SelectItem value="weekly">Weekly</SelectItem>
                <SelectItem value="monthly">Monthly</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {value.type === "specific" && value.frequency !== "hourly" && (
            <div>
              <Label htmlFor="specific-time">At time</Label>
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
              <Label htmlFor="day-of-week">Day of week</Label>
              <Select
                value={value.day_of_week?.toString() || "1"}
                onValueChange={(v) => handleSpecificChange("day_of_week", parseInt(v))}
                disabled={disabled}
              >
                <SelectTrigger id="day-of-week" className="mt-1.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">Monday</SelectItem>
                  <SelectItem value="2">Tuesday</SelectItem>
                  <SelectItem value="3">Wednesday</SelectItem>
                  <SelectItem value="4">Thursday</SelectItem>
                  <SelectItem value="5">Friday</SelectItem>
                  <SelectItem value="6">Saturday</SelectItem>
                  <SelectItem value="0">Sunday</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          {value.type === "specific" && value.frequency === "monthly" && (
            <div>
              <Label htmlFor="day-of-month">Day of month</Label>
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
              {value.frequency === "hourly" && "Runs every hour at minute 0"}
              {value.frequency === "daily" && `Runs daily at ${value.time || "00:00"}`}
              {value.frequency === "weekly" && `Runs on ${["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][value.day_of_week ?? 1]} at ${value.time || "00:00"}`}
              {value.frequency === "monthly" && `Runs on day ${value.day_of_month ?? 1} of each month at ${value.time || "00:00"}`}
            </p>
          )}
        </TabsContent>

        <TabsContent value="advanced" className="space-y-4 mt-4">
          <div>
            <Label htmlFor="cron-expr">Cron expression</Label>
            <Input
              id="cron-expr"
              value={value.type === "advanced" ? value.advanced : ""}
              onChange={(e) => handleAdvancedChange(e.target.value)}
              disabled={disabled}
              placeholder="0 * * * *"
              className="mt-1.5 font-mono"
            />
            <p className="text-xs text-muted-foreground mt-1.5">
              Standard 5-field cron format: minute hour day month day-of-week
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
