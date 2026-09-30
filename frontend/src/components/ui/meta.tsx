"use client";

import {
  Bug,
  CheckSquare,
  Sparkles,
  TrendingUp,
  BookOpen,
  Layers,
  Circle,
  SignalHigh,
  SignalMedium,
  SignalLow,
  AlertTriangle,
  Minus,
} from "lucide-react";
import type { IssueType, Priority, Status, Label } from "@/lib/types";
import { cn, dueState, formatDueLabel } from "@/lib/utils";

const TYPE_ICONS: Record<string, typeof Bug> = {
  bug: Bug,
  task: CheckSquare,
  feature: Sparkles,
  improvement: TrendingUp,
  documentation: BookOpen,
  epic: Layers,
};

export function TypeIcon({ type, size = 14 }: { type: IssueType; size?: number }) {
  const Icon = TYPE_ICONS[type.key] || Circle;
  return <Icon size={size} style={{ color: type.color }} aria-label={type.name} />;
}

const PRIORITY_ICONS: Record<string, typeof SignalHigh> = {
  urgent: AlertTriangle,
  high: SignalHigh,
  medium: SignalMedium,
  low: SignalLow,
  none: Minus,
};

export function PriorityIcon({ priority, size = 14 }: { priority: Priority; size?: number }) {
  const Icon = PRIORITY_ICONS[priority.key] || Minus;
  return <Icon size={size} style={{ color: priority.color }} aria-label={priority.name} />;
}

export function PriorityBadge({ priority }: { priority: Priority }) {
  return (
    <span className="inline-flex items-center gap-1 text-xs text-fg-subtle" title={`Priority: ${priority.name}`}>
      <PriorityIcon priority={priority} />
      {priority.name}
    </span>
  );
}

export function StatusPill({ status }: { status: Status }) {
  return (
    <span className="badge" style={{ background: `${status.color}20`, color: status.color }}>
      <Circle size={8} fill={status.color} stroke="none" />
      {status.name}
    </span>
  );
}

export function LabelChip({ label }: { label: Label }) {
  return (
    <span
      className="badge"
      style={{ background: `${label.color}18`, color: label.color, border: `1px solid ${label.color}30` }}
    >
      {label.name}
    </span>
  );
}

export function DueBadge({ due, isOverdue }: { due: string | null; isOverdue?: boolean }) {
  if (!due) return null;
  const state = dueState(due, isOverdue);
  const styles: Record<string, string> = {
    overdue: "text-red-600 dark:text-red-400 bg-red-500/10",
    today: "text-amber-700 dark:text-amber-400 bg-amber-500/10",
    tomorrow: "text-fg-subtle bg-surface-2",
    upcoming: "text-fg-subtle bg-surface-2",
    none: "",
  };
  return (
    <span className={cn("badge", styles[state])} title={`Due ${due}`}>
      {formatDueLabel(due)}
    </span>
  );
}
