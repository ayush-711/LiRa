"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  useIssue, useIssueComments, useIssueActivity, useIssueRelationships,
  useIssueSubtasks, useIssueAttachments, useMeta, useProjectMembers,
} from "@/lib/queries";
import { api, ApiError, apiBase } from "@/lib/api";
import { useAuth, canWrite } from "@/lib/auth";
import { useToast } from "@/lib/toast";
import { Avatar } from "@/components/ui/Avatar";
import { TypeIcon, PriorityIcon, StatusPill, DueBadge } from "@/components/ui/meta";
import { CenterSpinner, Spinner } from "@/components/ui/misc";
import { InlineSelect } from "@/components/issue/InlineSelect";
import { CreateIssueModal } from "@/components/CreateIssueModal";
import { LabelPicker, LabelChipList } from "@/components/LabelPicker";
import { Markdown } from "@/components/ui/Markdown";
import { MentionTextarea } from "@/components/issue/MentionTextarea";
import { relativeTime, fullDate, formatBytes, cn } from "@/lib/utils";
import { Paperclip, Plus, X, Link2, MessageSquare, ListTree, Trash2, Download } from "lucide-react";

export function issueDetailInvalidateQueryKeys(issueKey: string) {
  return [
    ["issue", issueKey],
    ["activity", issueKey],
    ["board"],
    ["issues"],
    ["my-issues"],
  ] as const;
}

export function IssueDetailView({ issueKey, compact }: { issueKey: string; compact?: boolean }) {
  const { data: issue, isLoading } = useIssue(issueKey);
  const { user } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const writable = canWrite(user);

  const invalidate = () => {
    issueDetailInvalidateQueryKeys(issueKey).forEach((queryKey) => {
      qc.invalidateQueries({ queryKey: [...queryKey] });
    });
  };

  async function patch(body: Record<string, unknown>) {
    try {
      await api(`/issues/${issueKey}`, { method: "PATCH", body });
      invalidate();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Update failed", "error");
    }
  }

  if (isLoading || !issue) return <CenterSpinner />;

  return (
    <div className={cn("grid gap-6", compact ? "grid-cols-1" : "lg:grid-cols-[1fr_260px]")}>
      {/* Main column */}
      <div className="min-w-0 space-y-6 p-5">
        <div>
          <div className="mb-1 flex items-center gap-2 text-xs text-muted">
            <TypeIcon type={issue.type} />
            <Link href={`/projects/${issue.project_key}`} className="hover:text-fg">{issue.project_key}</Link>
            <span>/</span>
            <span className="font-mono">{issue.key}</span>
          </div>
          <IssueTitle issue={issue} writable={writable} onSave={(title) => patch({ title })} />
        </div>

        <DescriptionEditor
          value={issue.description}
          writable={writable}
          onSave={(description) => patch({ description })}
        />

        <SubtasksSection issueKey={issueKey} projectKey={issue.project_key!} writable={writable} onChange={invalidate} />
        <RelationshipsSection issueKey={issueKey} writable={writable} />
        <AttachmentsSection issueKey={issueKey} writable={writable} />
        <CommentsSection issueKey={issueKey} projectKey={issue.project_key!} writable={writable} />
        <ActivitySection issueKey={issueKey} />
      </div>

      {/* Metadata panel */}
      <aside className={cn("space-y-4 border-l bg-surface p-4", compact && "border-l-0 border-t")}>
        <MetaPanel issue={issue} writable={writable} patch={patch} />
      </aside>
    </div>
  );
}

function IssueTitle({ issue, writable, onSave }: { issue: any; writable: boolean; onSave: (v: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(issue.title);
  if (editing) {
    return (
      <input autoFocus className="input text-lg font-semibold" value={value}
        onChange={(e) => setValue(e.target.value)}
        onBlur={() => { setEditing(false); if (value.trim() && value !== issue.title) onSave(value.trim()); }}
        onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }} />
    );
  }
  return (
    <h1 className={cn("text-lg font-semibold leading-snug", writable && "cursor-text hover:bg-surface-2 rounded")}
      onClick={() => writable && (setValue(issue.title), setEditing(true))}>
      {issue.title}
    </h1>
  );
}

function DescriptionEditor({ value, writable, onSave }: { value: string | null; writable: boolean; onSave: (v: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [preview, setPreview] = useState(false);
  const [draft, setDraft] = useState(value || "");

  if (editing) {
    return (
      <div>
        <div className="mb-1.5 flex items-center gap-1 text-xs">
          <button onClick={() => setPreview(false)}
            className={cn("rounded px-2 py-1", !preview ? "bg-surface-2 font-medium" : "text-muted hover:text-fg")}>
            Write
          </button>
          <button onClick={() => setPreview(true)}
            className={cn("rounded px-2 py-1", preview ? "bg-surface-2 font-medium" : "text-muted hover:text-fg")}>
            Preview
          </button>
          <span className="ml-auto text-muted">Markdown supported</span>
        </div>
        {preview ? (
          <div className="min-h-[10rem] rounded-lg border bg-surface p-3">
            {draft.trim() ? <Markdown>{draft}</Markdown> : <span className="text-sm text-muted">Nothing to preview.</span>}
          </div>
        ) : (
          <textarea autoFocus className="input h-40 py-2 font-mono text-sm" value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Describe the issue… **bold**, `code`, - lists, # headings" />
        )}
        <div className="mt-2 flex gap-2">
          <button className="btn-primary" onClick={() => { onSave(draft); setEditing(false); setPreview(false); }}>Save</button>
          <button className="btn-outline" onClick={() => { setDraft(value || ""); setEditing(false); setPreview(false); }}>Cancel</button>
        </div>
      </div>
    );
  }
  return (
    <div className={cn("min-h-[3rem] rounded", writable && "cursor-text hover:bg-surface-2")}
      onClick={() => writable && (setDraft(value || ""), setEditing(true))}>
      {value ? <Markdown>{value}</Markdown> : <span className="text-sm text-muted">{writable ? "Add a description…" : "No description."}</span>}
    </div>
  );
}

function MetaPanel({ issue, writable, patch }: any) {
  const { data: meta } = useMeta();
  const { data: members } = useProjectMembers(issue.project_key);
  const memberUsers = members?.map((m) => m.user) || [];

  return (
    <div className="space-y-3.5 text-sm">
      <Field label="Status">
        <InlineSelect label="Status" value={issue.status} options={meta?.statuses || []} disabled={!writable}
          onChange={(id) => id && patch({ status_id: id })}
          render={(s) => (s ? <StatusPill status={s} /> : <span className="text-muted">—</span>)} />
      </Field>
      <Field label="Assignee">
        <InlineSelect label="Assignee" value={issue.assignee} options={memberUsers as any} disabled={!writable}
          onChange={(id) => patch({ assignee_id: id })}
          render={(u: any) => u ? (
            <span className="flex items-center gap-1.5"><Avatar user={u} size={20} /> {u.name}</span>
          ) : <span className="flex items-center gap-1.5 text-muted"><span className="inline-block h-5 w-5 rounded-full border border-dashed" /> Unassigned</span>} />
      </Field>
      <Field label="Priority">
        <InlineSelect label="Priority" value={issue.priority} options={meta?.priorities || []} disabled={!writable}
          onChange={(id) => id && patch({ priority_id: id })}
          render={(p) => p ? <span className="flex items-center gap-1.5"><PriorityIcon priority={p} /> {p.name}</span> : <span className="text-muted">—</span>} />
      </Field>
      <Field label="Type">
        <InlineSelect label="Type" value={issue.type} options={meta?.types || []} disabled={!writable}
          onChange={(id) => id && patch({ type_id: id })}
          render={(t) => t ? <span className="flex items-center gap-1.5"><TypeIcon type={t} /> {t.name}</span> : <span className="text-muted">—</span>} />
      </Field>
      <Field label="Due date">
        {writable ? (
          <input type="date" className="input h-8" value={issue.due_date || ""}
            onChange={(e) => patch({ due_date: e.target.value || null })} />
        ) : issue.due_date ? <DueBadge due={issue.due_date} isOverdue={issue.is_overdue} /> : <span className="text-muted">—</span>}
      </Field>
      <Field label="Estimate">
        {writable ? (
          <input type="number" min={0} max={1000} className="input h-8"
            placeholder="Points"
            defaultValue={issue.estimate ?? ""}
            onBlur={(e) => {
              const raw = e.target.value.trim();
              const next = raw === "" ? null : Number(raw);
              if (next !== (issue.estimate ?? null)) patch({ estimate: next });
            }} />
        ) : (
          <span className={issue.estimate == null ? "text-muted" : ""}>
            {issue.estimate ?? "—"}
          </span>
        )}
      </Field>
      <Field label="Labels">
        {writable ? (
          <LabelPicker
            value={issue.labels.map((l: any) => l.id)}
            onChange={(ids) => patch({ label_ids: ids })}
          />
        ) : (
          <LabelChipList value={issue.labels.map((l: any) => l.id)} labels={issue.labels} />
        )}
      </Field>
      <div className="border-t pt-3 text-xs text-muted">
        <div>Reporter: {issue.reporter?.name || "—"}</div>
        <div className="mt-1" title={fullDate(issue.created_at)}>Created {relativeTime(issue.created_at)}</div>
        <div title={fullDate(issue.updated_at)}>Updated {relativeTime(issue.updated_at)}</div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="label-text mb-1">{label}</div>
      {children}
    </div>
  );
}

function SubtasksSection({ issueKey, projectKey, writable, onChange }: any) {
  const { data: subtasks } = useIssueSubtasks(issueKey);
  const { data: issue } = useIssue(issueKey);
  const [createOpen, setCreateOpen] = useState(false);
  if (!subtasks) return null;
  const done = issue?.subtask_done ?? 0;
  const total = issue?.subtask_total ?? 0;
  return (
    <section>
      <SectionHeader icon={<ListTree size={15} />} title="Subtasks"
        extra={total > 0 ? <span className="text-xs text-muted">{done}/{total} done</span> : undefined}
        action={writable && <button className="btn-ghost h-7 px-2 text-xs" onClick={() => setCreateOpen(true)}><Plus size={13} /> Add</button>} />
      {subtasks.length === 0 ? (
        <p className="text-sm text-muted">No subtasks.</p>
      ) : (
        <div className="divide-y rounded-md border">
          {subtasks.map((s) => (
            <Link key={s.id} href={`/issues/${s.key}`} className="flex items-center gap-2 px-3 py-1.5 text-sm hover:bg-surface-2">
              <TypeIcon type={s.type} />
              <span className="font-mono text-xs text-muted">{s.key}</span>
              <span className="min-w-0 flex-1 truncate">{s.title}</span>
              <StatusPill status={s.status} />
            </Link>
          ))}
        </div>
      )}
      <CreateIssueModal open={createOpen} onClose={() => setCreateOpen(false)}
        defaultProjectKey={projectKey} parentId={issue?.id}
        onCreated={() => { setCreateOpen(false); onChange(); }} />
    </section>
  );
}

function RelationshipsSection({ issueKey, writable }: any) {
  const { data: rels } = useIssueRelationships(issueKey);
  const qc = useQueryClient();
  const toast = useToast();
  const [adding, setAdding] = useState(false);
  const [targetKey, setTargetKey] = useState("");
  const [type, setType] = useState("blocks");

  async function add() {
    try {
      await api(`/issues/${issueKey}/relationships`, { method: "POST", body: { target_key: targetKey.toUpperCase(), type } });
      qc.invalidateQueries({ queryKey: ["relationships", issueKey] });
      setTargetKey(""); setAdding(false);
    } catch (err) { toast(err instanceof ApiError ? err.message : "Failed", "error"); }
  }
  async function remove(id: number) {
    await api(`/relationships/${id}`, { method: "DELETE" });
    qc.invalidateQueries({ queryKey: ["relationships", issueKey] });
  }

  const labelFor = (r: any) =>
    r.type === "relates_to" ? "Related to" : r.direction === "outgoing" ? "Blocks" : "Blocked by";

  if (!rels) return null;
  return (
    <section>
      <SectionHeader icon={<Link2 size={15} />} title="Relationships"
        action={writable && <button className="btn-ghost h-7 px-2 text-xs" onClick={() => setAdding((a) => !a)}><Plus size={13} /> Link</button>} />
      {adding && (
        <div className="mb-2 flex items-center gap-2">
          <select className="input h-8 w-32" value={type} onChange={(e) => setType(e.target.value)}>
            <option value="blocks">Blocks</option>
            <option value="relates_to">Relates to</option>
          </select>
          <input className="input h-8 font-mono uppercase" placeholder="DOC-125" value={targetKey}
            onChange={(e) => setTargetKey(e.target.value)} />
          <button className="btn-primary h-8" onClick={add}>Add</button>
        </div>
      )}
      {rels.length === 0 ? (
        <p className="text-sm text-muted">No linked issues.</p>
      ) : (
        <div className="space-y-1">
          {rels.map((r) => (
            <div key={r.relationship_id} className="flex items-center gap-2 text-sm">
              <span className="w-20 shrink-0 text-xs font-medium text-muted">{labelFor(r)}</span>
              <Link href={`/issues/${r.issue.key}`} className="flex min-w-0 flex-1 items-center gap-1.5 hover:text-brand">
                <TypeIcon type={r.issue.type} />
                <span className="font-mono text-xs">{r.issue.key}</span>
                <span className="truncate">{r.issue.title}</span>
              </Link>
              {writable && <button onClick={() => remove(r.relationship_id)} className="text-muted hover:text-red-600"><X size={13} /></button>}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function AttachmentsSection({ issueKey, writable }: any) {
  const { data: attachments } = useIssueAttachments(issueKey);
  const qc = useQueryClient();
  const toast = useToast();
  const [uploading, setUploading] = useState(false);

  async function upload(file: File) {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      await api(`/issues/${issueKey}/attachments`, { method: "POST", formData: fd });
      qc.invalidateQueries({ queryKey: ["attachments", issueKey] });
      qc.invalidateQueries({ queryKey: ["issue", issueKey] });
    } catch (err) { toast(err instanceof ApiError ? err.message : "Upload failed", "error"); }
    finally { setUploading(false); }
  }
  async function remove(id: number) {
    await api(`/attachments/${id}`, { method: "DELETE" });
    qc.invalidateQueries({ queryKey: ["attachments", issueKey] });
  }
  if (!attachments) return null;
  return (
    <section>
      <SectionHeader icon={<Paperclip size={15} />} title="Attachments"
        action={writable && (
          <label className="btn-ghost h-7 cursor-pointer px-2 text-xs">
            {uploading ? <Spinner /> : <><Plus size={13} /> Upload</>}
            <input type="file" className="hidden" disabled={uploading}
              onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
          </label>
        )} />
      {attachments.length === 0 ? (
        <p className="text-sm text-muted">No attachments.</p>
      ) : (
        <div className="space-y-1">
          {attachments.map((a) => (
            <div key={a.id} className="flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm">
              <Paperclip size={13} className="text-muted" />
              <span className="min-w-0 flex-1 truncate">{a.original_filename}</span>
              <span className="text-xs text-muted">{formatBytes(a.size_bytes)}</span>
              <a href={`${apiBase}/attachments/${a.id}/download`} className="text-muted hover:text-brand"><Download size={14} /></a>
              {writable && <button onClick={() => remove(a.id)} className="text-muted hover:text-red-600"><Trash2 size={13} /></button>}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function CommentsSection({ issueKey, projectKey, writable }: any) {
  const { data: comments } = useIssueComments(issueKey);
  const { data: members } = useProjectMembers(projectKey);
  const { user } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const [body, setBody] = useState("");
  const [posting, setPosting] = useState(false);

  async function post() {
    if (!body.trim()) return;
    setPosting(true);
    try {
      await api(`/issues/${issueKey}/comments`, { method: "POST", body: { body } });
      setBody("");
      qc.invalidateQueries({ queryKey: ["comments", issueKey] });
      qc.invalidateQueries({ queryKey: ["activity", issueKey] });
      qc.invalidateQueries({ queryKey: ["issue", issueKey] });
    } catch (err) { toast(err instanceof ApiError ? err.message : "Failed", "error"); }
    finally { setPosting(false); }
  }
  if (!comments) return null;
  return (
    <section>
      <SectionHeader icon={<MessageSquare size={15} />} title={`Comments (${comments.length})`} />
      <div className="space-y-3">
        {comments.map((c) => (
          <div key={c.id} className="flex gap-2.5">
            <Avatar user={c.author} size={28} />
            <div className="min-w-0 flex-1">
              <div className="text-sm">
                <span className="font-medium">{c.author?.name || "Unknown"}</span>
                <span className="ml-1.5 text-xs text-muted">{relativeTime(c.created_at)}{c.edited_at ? " · edited" : ""}</span>
              </div>
              <Markdown>{c.body}</Markdown>
            </div>
          </div>
        ))}
        {comments.length === 0 && <p className="text-sm text-muted">No comments yet.</p>}
      </div>
      {writable && (
        <div className="mt-3 flex gap-2.5">
          <Avatar user={user} size={28} />
          <div className="flex-1">
            <MentionTextarea
              value={body}
              onChange={setBody}
              people={(members || []).map((m: any) => m.user)}
              placeholder="Add a comment… type @ to mention someone"
              className="h-16"
              onSubmit={post}
            />
            <div className="mt-1.5 flex items-center justify-end gap-2">
              <span className="text-xs text-muted">Markdown supported · ⌘↵ to send</span>
              <button className="btn-primary" onClick={post} disabled={posting || !body.trim()}>
                {posting ? <Spinner className="text-white" /> : "Comment"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function ActivitySection({ issueKey }: any) {
  const { data: activity } = useIssueActivity(issueKey);
  if (!activity || activity.length === 0) return null;
  return (
    <section>
      <SectionHeader title="Activity" />
      <div className="space-y-2">
        {activity.map((a) => (
          <div key={a.id} className="flex items-center gap-2 text-xs text-muted">
            <Avatar user={a.actor} size={18} />
            <span className="text-fg-subtle">{a.text}</span>
            <span title={fullDate(a.created_at)}>· {relativeTime(a.created_at)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function SectionHeader({ icon, title, action, extra }: { icon?: React.ReactNode; title: string; action?: React.ReactNode; extra?: React.ReactNode }) {
  return (
    <div className="mb-2 flex items-center gap-2">
      {icon && <span className="text-muted">{icon}</span>}
      <h3 className="text-sm font-semibold">{title}</h3>
      {extra}
      <div className="ml-auto">{action}</div>
    </div>
  );
}
