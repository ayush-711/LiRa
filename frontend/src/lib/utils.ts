import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { formatDistanceToNow, format, isToday, isTomorrow, isPast, parseISO } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

// Deterministic avatar colour from a string.
export function avatarColor(seed: string): string {
  const colors = ["#6366f1", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444",
    "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"];
  let hash = 0;
  for (let i = 0; i < seed.length; i++) hash = seed.charCodeAt(i) + ((hash << 5) - hash);
  return colors[Math.abs(hash) % colors.length];
}

export function relativeTime(iso: string): string {
  try {
    return formatDistanceToNow(parseISO(iso), { addSuffix: true });
  } catch {
    return iso;
  }
}

export function fullDate(iso: string): string {
  try {
    return format(parseISO(iso), "d MMM yyyy, HH:mm");
  } catch {
    return iso;
  }
}

export type DueState = "none" | "overdue" | "today" | "tomorrow" | "upcoming";

export function dueState(due: string | null, isOverdue?: boolean): DueState {
  if (!due) return "none";
  const d = parseISO(due);
  if (isOverdue) return "overdue";
  if (isToday(d)) return "today";
  if (isTomorrow(d)) return "tomorrow";
  if (isPast(d)) return "overdue";
  return "upcoming";
}

export function formatDueLabel(due: string | null): string {
  if (!due) return "";
  const d = parseISO(due);
  if (isToday(d)) return "Today";
  if (isTomorrow(d)) return "Tomorrow";
  return format(d, "d MMM");
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export const ROLE_LABELS: Record<string, string> = {
  admin: "Admin",
  project_manager: "Project Manager",
  member: "Member",
  viewer: "Viewer",
};
