// API types mirroring the backend Pydantic schemas.

export type GlobalRole = "admin" | "project_manager" | "member" | "viewer";
export type ProjectRole = "manager" | "member";
export type ProjectStatus = "planning" | "active" | "completed" | "archived";
export type RelationshipType = "blocks" | "relates_to";

export interface User {
  id: number;
  name: string;
  email: string;
  avatar_url: string | null;
  role: GlobalRole;
  is_active: boolean;
}

export interface UserWithStats extends User {
  assigned: number;
  in_progress: number;
  overdue: number;
  last_login_at: string | null;
}

export interface Status {
  id: number;
  key: string;
  name: string;
  category: "backlog" | "todo" | "in_progress" | "done";
  order_index: number;
  color: string;
}
export interface IssueType {
  id: number;
  key: string;
  name: string;
  icon: string;
  color: string;
}
export interface Priority {
  id: number;
  key: string;
  name: string;
  rank: number;
  color: string;
}
export interface Meta {
  statuses: Status[];
  types: IssueType[];
  priorities: Priority[];
}

export interface Label {
  id: number;
  name: string;
  color: string;
  description?: string | null;
  is_archived?: boolean;
}

export interface Project {
  id: number;
  key: string;
  name: string;
  description: string | null;
  status: ProjectStatus;
  priority: string | null;
  start_date: string | null;
  target_date: string | null;
  lead_id: number | null;
  created_at: string;
  my_role: ProjectRole | null;
}

export interface ProjectMember {
  id: number;
  role: ProjectRole;
  user: User;
}

export interface ProjectStats {
  total_issues: number;
  open_issues: number;
  in_progress: number;
  done: number;
  overdue: number;
  urgent: number;
  completion: number;
}

export interface IssueSummary {
  id: number;
  key: string;
  title: string;
  project_id: number;
  project_key: string | null;
  type: IssueType;
  status: Status;
  priority: Priority;
  assignee: User | null;
  reporter: User | null;
  labels: Label[];
  due_date: string | null;
  estimate: number | null;
  parent_id: number | null;
  board_rank: number;
  is_overdue: boolean;
  updated_at: string;
  created_at: string;
}

export interface IssueDetail extends IssueSummary {
  description: string | null;
  resolved_at: string | null;
  completed_at: string | null;
  subtask_total: number;
  subtask_done: number;
  comment_count: number;
  attachment_count: number;
}

export interface RelatedIssue {
  relationship_id: number;
  type: RelationshipType;
  direction: "outgoing" | "incoming";
  issue: IssueSummary;
}

export interface Comment {
  id: number;
  body: string;
  author: User | null;
  created_at: string;
  edited_at: string | null;
}

export interface Attachment {
  id: number;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  uploaded_by: User | null;
  created_at: string;
}

export interface Activity {
  id: number;
  event_type: string;
  actor: User | null;
  field: string | null;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
  text: string;
}

export interface Notification {
  id: number;
  type: string;
  title: string;
  body: string | null;
  issue_id: number | null;
  actor: User | null;
  is_read: boolean;
  created_at: string;
  meta: Record<string, unknown> | null;
}

export interface AuditEntry {
  id: number;
  action: string;
  actor: User | null;
  entity_type: string | null;
  entity_id: string | null;
  meta: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}

export interface Invitation {
  id: number;
  email: string;
  role: GlobalRole;
  created_at: string;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  is_pending: boolean;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface BoardColumn {
  status: Status;
  issues: IssueSummary[];
}
export interface Board {
  columns: BoardColumn[];
}

export interface DashboardData {
  overview: {
    active_projects: number;
    open_issues: number;
    overdue_issues: number;
    urgent_issues: number;
    completed_recently: number;
  };
  personal: {
    my_open: number;
    my_overdue: number;
    my_urgent: number;
    my_upcoming: number;
  };
  issues_by_status: { id: number; name: string; color: string; count: number }[];
  projects: {
    id: number;
    key: string;
    name: string;
    status: string;
    total_issues: number;
    done_issues: number;
    completion: number;
    last_activity_at: string | null;
  }[];
  workload: { user_id: number; assigned: number; in_progress: number; overdue: number }[];
  throughput: { week: string; count: number; points: number }[];
  recent_activity: Activity[];
}

export interface NotificationPreferences {
  email_on_assignment: boolean;
  email_on_mention: boolean;
  email_on_comment: boolean;
  email_on_due_reminder: boolean;
  email_on_status_change: boolean;
}

export interface SavedView {
  id: number;
  name: string;
  project_id: number | null;
  filters: Record<string, string | number | boolean>;
  is_shared: boolean;
  owner_id: number;
  created_at: string;
}
