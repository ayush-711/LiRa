"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import type {
  Attachment,
  AuditEntry,
  Board,
  Comment,
  DashboardData,
  IssueDetail,
  IssueSummary,
  Invitation,
  Label,
  Meta,
  Notification,
  NotificationPreferences,
  Page,
  Project,
  ProjectMember,
  ProjectStats,
  RelatedIssue,
  Status,
  SavedView,
  Activity,
  UserWithStats,
} from "./types";

export function useMeta() {
  return useQuery({ queryKey: ["meta"], queryFn: () => api<Meta>("/meta"), staleTime: 5 * 60_000 });
}

export function useProjects(includeArchived = false) {
  return useQuery({
    queryKey: ["projects", includeArchived],
    queryFn: () => api<Project[]>(`/projects?include_archived=${includeArchived}`),
  });
}

export function useProject(key: string) {
  return useQuery({ queryKey: ["project", key], queryFn: () => api<Project>(`/projects/${key}`), enabled: !!key });
}

export function useProjectStats(key: string) {
  return useQuery({ queryKey: ["project-stats", key], queryFn: () => api<ProjectStats>(`/projects/${key}/stats`), enabled: !!key });
}

export function useProjectMembers(key: string) {
  return useQuery({ queryKey: ["members", key], queryFn: () => api<ProjectMember[]>(`/projects/${key}/members`), enabled: !!key });
}

export function useBoard(key: string, filters: Record<string, string | number | boolean> = {}) {
  const qs = new URLSearchParams(
    Object.entries(filters).filter(([, v]) => v !== "" && v !== false && v != null)
      .map(([k, v]) => [k, String(v)])
  ).toString();
  return useQuery({
    queryKey: ["board", key, qs],
    queryFn: () => api<Board>(`/projects/${key}/board${qs ? `?${qs}` : ""}`),
    enabled: !!key,
  });
}

export function useIssues(params: Record<string, string | number | boolean | undefined>) {
  const qs = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== "" && v !== false)
      .map(([k, v]) => [k, String(v)])
  ).toString();
  return useQuery({
    queryKey: ["issues", qs],
    queryFn: () => api<Page<IssueSummary>>(`/issues${qs ? `?${qs}` : ""}`),
  });
}

export function useIssue(key: string) {
  return useQuery({ queryKey: ["issue", key], queryFn: () => api<IssueDetail>(`/issues/${key}`), enabled: !!key });
}

export function useIssueComments(key: string) {
  return useQuery({ queryKey: ["comments", key], queryFn: () => api<Comment[]>(`/issues/${key}/comments`), enabled: !!key });
}

export function useIssueActivity(key: string) {
  return useQuery({ queryKey: ["activity", key], queryFn: () => api<Activity[]>(`/issues/${key}/activity`), enabled: !!key });
}

export function useIssueRelationships(key: string) {
  return useQuery({ queryKey: ["relationships", key], queryFn: () => api<RelatedIssue[]>(`/issues/${key}/relationships`), enabled: !!key });
}

export function useIssueSubtasks(key: string) {
  return useQuery({ queryKey: ["subtasks", key], queryFn: () => api<IssueSummary[]>(`/issues/${key}/subtasks`), enabled: !!key });
}

export function useIssueAttachments(key: string) {
  return useQuery({ queryKey: ["attachments", key], queryFn: () => api<Attachment[]>(`/issues/${key}/attachments`), enabled: !!key });
}

export function useLabels() {
  return useQuery({ queryKey: ["labels"], queryFn: () => api<Label[]>("/labels"), staleTime: 60_000 });
}

export function useTeam() {
  return useQuery({ queryKey: ["team"], queryFn: () => api<UserWithStats[]>("/users") });
}

export function useDashboard() {
  return useQuery({ queryKey: ["dashboard"], queryFn: () => api<DashboardData>("/dashboard") });
}

export interface MyIssuesResponse {
  groups: { status: Status; issues: IssueSummary[] }[];
  total: number;
}

export function useMyIssues(sort = "priority") {
  return useQuery({
    queryKey: ["my-issues", sort],
    queryFn: () => api<MyIssuesResponse>(`/my-issues?sort=${sort}`),
  });
}

export function useNotifications() {
  return useQuery({ queryKey: ["notifications"], queryFn: () => api<Notification[]>("/notifications"), refetchInterval: 60_000 });
}

export function useUnreadCount() {
  return useQuery({ queryKey: ["unread"], queryFn: () => api<{ count: number }>("/notifications/unread-count"), refetchInterval: 60_000 });
}

export function useNotificationPrefs() {
  return useQuery({ queryKey: ["notif-prefs"], queryFn: () => api<NotificationPreferences>("/account/notification-preferences") });
}

export function useInvitations() {
  return useQuery({ queryKey: ["invitations"], queryFn: () => api<Invitation[]>("/invitations") });
}

export function useSavedViews(projectId?: number) {
  return useQuery({
    queryKey: ["saved-views", projectId ?? null],
    queryFn: () => api<SavedView[]>(`/saved-views${projectId ? `?project_id=${projectId}` : ""}`),
  });
}

export function useAudit(params: Record<string, string | number | undefined>) {
  const qs = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== "").map(([k, v]) => [k, String(v)])
  ).toString();
  return useQuery({ queryKey: ["audit", qs], queryFn: () => api<Page<AuditEntry>>(`/audit-logs${qs ? `?${qs}` : ""}`) });
}
