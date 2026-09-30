"use client";

import { useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Search, X, Bookmark, BookmarkPlus, Trash2 } from "lucide-react";
import {
  useIssues, useMeta, useProjectMembers, useProject, useSavedViews, useLabels,
} from "@/lib/queries";
import { api, ApiError } from "@/lib/api";
import { useAuth, canWrite } from "@/lib/auth";
import { useToast } from "@/lib/toast";
import { CenterSpinner, EmptyState } from "@/components/ui/misc";
import { Avatar } from "@/components/ui/Avatar";
import { TypeIcon, PriorityIcon, StatusPill, LabelChip, DueBadge } from "@/components/ui/meta";
import { relativeTime, cn } from "@/lib/utils";
import type { IssueSummary } from "@/lib/types";

type Filters = {
  search: string;
  status: number | "";
  priority: number | "";
  assignee: number | "";
  sort: string;
  order: "asc" | "desc";
};

const EMPTY: Filters = { search: "", status: "", priority: "", assignee: "", sort: "updated", order: "desc" };

export default function ProjectIssuesPage() {
  const { key } = useParams<{ key: string }>();
  const { data: project } = useProject(key);
  const { data: meta } = useMeta();
  const { data: members } = useProjectMembers(key);
  const { data: labels } = useLabels();
  const { data: views } = useSavedViews(project?.id);
  const { user } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const writable = canWrite(user);

  const [f, setF] = useState<Filters>(EMPTY);
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const limit = 30;

  const set = <K extends keyof Filters>(k: K, v: Filters[K]) => {
    setF((prev) => ({ ...prev, [k]: v }));
    setOffset(0);
  };

  const { data, isLoading } = useIssues({
    project: key, search: f.search || undefined, status: f.status || undefined,
    priority: f.priority || undefined, assignee: f.assignee || undefined,
    sort: f.sort, order: f.order, limit, offset, include_subtasks: true,
  });

  const items = data?.items || [];
  const allSelected = items.length > 0 && items.every((i) => selected.has(i.key));
  const activeFilterCount = useMemo(
    () => [f.search, f.status, f.priority, f.assignee].filter(Boolean).length,
    [f]
  );

  function toggle(k: string) {
    setSelected((s) => {
      const next = new Set(s);
      next.has(k) ? next.delete(k) : next.add(k);
      return next;
    });
  }

  async function bulk(body: Record<string, unknown>) {
    setBusy(true);
    try {
      const res = await api<{ updated: number; failed: { key: string; error: string }[] }>(
        "/issues/bulk", { method: "POST", body: { keys: [...selected], ...body } }
      );
      qc.invalidateQueries();
      if (res.failed.length) {
        toast(`Updated ${res.updated}; ${res.failed.length} failed (${res.failed[0].error})`, "error");
      } else {
        toast(`Updated ${res.updated} issue${res.updated === 1 ? "" : "s"}`);
      }
      setSelected(new Set());
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Bulk update failed", "error");
    } finally {
      setBusy(false);
    }
  }

  async function saveView() {
    const name = prompt("Name this view");
    if (!name?.trim() || !project) return;
    try {
      await api("/saved-views", {
        method: "POST",
        body: { name: name.trim(), project_id: project.id, filters: f as any },
      });
      qc.invalidateQueries({ queryKey: ["saved-views"] });
      toast("View saved");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Couldn't save view", "error");
    }
  }

  async function deleteView(id: number) {
    await api(`/saved-views/${id}`, { method: "DELETE" });
    qc.invalidateQueries({ queryKey: ["saved-views"] });
  }

  return (
    <div className="flex h-full flex-col">
      {/* Saved views */}
      {views && views.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 border-b bg-surface px-4 py-2">
          <Bookmark size={13} className="text-muted" />
          {views.map((v) => (
            <span key={v.id} className="group inline-flex items-center">
              <button
                onClick={() => { setF({ ...EMPTY, ...(v.filters as any) }); setOffset(0); }}
                className="badge bg-surface-2 text-fg-subtle hover:bg-brand-soft hover:text-brand"
              >
                {v.name}
                {v.is_shared && <span className="ml-1 text-[10px] text-muted">shared</span>}
              </button>
              {v.owner_id === user?.id && (
                <button onClick={() => deleteView(v.id)}
                  className="ml-0.5 text-muted opacity-0 transition-opacity hover:text-red-600 group-hover:opacity-100"
                  aria-label={`Delete view ${v.name}`}>
                  <Trash2 size={11} />
                </button>
              )}
            </span>
          ))}
        </div>
      )}

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2 border-b bg-surface px-4 py-2">
        <div className="flex h-8 min-w-[180px] flex-1 items-center gap-2 rounded-lg border px-2">
          <Search size={14} className="text-muted" />
          <input value={f.search} onChange={(e) => set("search", e.target.value)}
            placeholder="Search issues…" className="w-full bg-transparent text-sm outline-none" />
        </div>
        <select className="input h-8 w-auto" value={f.status} onChange={(e) => set("status", Number(e.target.value) || "")}>
          <option value="">All statuses</option>
          {meta?.statuses.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        <select className="input h-8 w-auto" value={f.priority} onChange={(e) => set("priority", Number(e.target.value) || "")}>
          <option value="">All priorities</option>
          {meta?.priorities.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select className="input h-8 w-auto" value={f.assignee} onChange={(e) => set("assignee", Number(e.target.value) || "")}>
          <option value="">All assignees</option>
          {members?.map((m) => <option key={m.user.id} value={m.user.id}>{m.user.name}</option>)}
        </select>
        <select className="input h-8 w-auto" value={`${f.sort}:${f.order}`}
          onChange={(e) => { const [s, o] = e.target.value.split(":"); setF((p) => ({ ...p, sort: s, order: o as "asc" | "desc" })); }}>
          <option value="updated:desc">Updated ↓</option>
          <option value="created:desc">Created ↓</option>
          <option value="due:asc">Due date ↑</option>
          <option value="key:asc">Key ↑</option>
        </select>
        {activeFilterCount > 0 && (
          <button className="btn-ghost h-8 px-2 text-xs" onClick={() => { setF(EMPTY); setOffset(0); }}>
            <X size={13} /> Clear
          </button>
        )}
        <button className="btn-outline h-8 px-2 text-xs" onClick={saveView} title="Save these filters as a view">
          <BookmarkPlus size={13} /> Save view
        </button>
      </div>

      {/* Table */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {isLoading ? <CenterSpinner /> : items.length === 0 ? (
          <div className="p-5"><EmptyState title="No issues found" description="Try adjusting your filters, or create a new issue." /></div>
        ) : (
          <div className="card m-4 overflow-hidden">
            {writable && (
              <div className="flex items-center gap-3 border-b bg-surface-2/50 px-3 py-1.5">
                <input type="checkbox" checked={allSelected} aria-label="Select all"
                  onChange={(e) => setSelected(e.target.checked ? new Set(items.map((i) => i.key)) : new Set())} />
                <span className="text-xs text-muted">
                  {selected.size > 0 ? `${selected.size} selected` : "Select issues for bulk actions"}
                </span>
              </div>
            )}
            {items.map((i) => (
              <Row key={i.id} issue={i} selectable={writable}
                checked={selected.has(i.key)} onToggle={() => toggle(i.key)} />
            ))}
          </div>
        )}
      </div>

      {/* Pagination */}
      {data && data.total > limit && (
        <div className="flex items-center justify-between border-t bg-surface px-4 py-2 text-sm">
          <span className="text-muted">{offset + 1}–{Math.min(offset + limit, data.total)} of {data.total}</span>
          <div className="flex gap-2">
            <button className="btn-outline h-8" disabled={offset === 0} onClick={() => setOffset((o) => Math.max(0, o - limit))}>Previous</button>
            <button className="btn-outline h-8" disabled={offset + limit >= data.total} onClick={() => setOffset((o) => o + limit)}>Next</button>
          </div>
        </div>
      )}

      {/* Bulk action bar */}
      {selected.size > 0 && (
        <div className="pointer-events-none fixed inset-x-0 bottom-5 z-40 flex justify-center px-4">
          <div className="pointer-events-auto flex flex-wrap items-center gap-2 rounded-xl border bg-surface px-3 py-2 shadow-pop">
            <span className="text-sm font-medium">{selected.size} selected</span>
            <span className="mx-1 h-5 w-px bg-border" />
            <select className="input h-8 w-auto" disabled={busy} value=""
              onChange={(e) => e.target.value && bulk({ status_id: Number(e.target.value) })}>
              <option value="">Status…</option>
              {meta?.statuses.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <select className="input h-8 w-auto" disabled={busy} value=""
              onChange={(e) => e.target.value && bulk({ priority_id: Number(e.target.value) })}>
              <option value="">Priority…</option>
              {meta?.priorities.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <select className="input h-8 w-auto" disabled={busy} value=""
              onChange={(e) => e.target.value && bulk({ assignee_id: Number(e.target.value) })}>
              <option value="">Assign to…</option>
              {members?.map((m) => <option key={m.user.id} value={m.user.id}>{m.user.name}</option>)}
            </select>
            <select className="input h-8 w-auto" disabled={busy} value=""
              onChange={(e) => e.target.value && bulk({ add_label_ids: [Number(e.target.value)] })}>
              <option value="">Add label…</option>
              {labels?.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
            <button className="btn-outline h-8 text-red-600" disabled={busy}
              onClick={() => confirm(`Archive ${selected.size} issue(s)?`) && bulk({ archive: true })}>
              Archive
            </button>
            <button className="btn-ghost h-8 px-2" onClick={() => setSelected(new Set())} aria-label="Clear selection">
              <X size={15} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Row({ issue, selectable, checked, onToggle }: {
  issue: IssueSummary; selectable: boolean; checked: boolean; onToggle: () => void;
}) {
  return (
    <div className={cn("flex items-center gap-3 border-b px-3 py-2 text-sm transition-colors hover:bg-surface-2",
      checked && "bg-brand-soft/60")}>
      {selectable && (
        <input type="checkbox" checked={checked} onChange={onToggle}
          aria-label={`Select ${issue.key}`} onClick={(e) => e.stopPropagation()} />
      )}
      <Link href={`/issues/${issue.key}`} className="flex min-w-0 flex-1 items-center gap-3">
        <TypeIcon type={issue.type} />
        <span className="w-16 shrink-0 font-mono text-xs text-muted">{issue.key}</span>
        <span className="min-w-0 flex-1 truncate">{issue.title}</span>
        <div className="hidden shrink-0 items-center gap-1 md:flex">
          {issue.labels.slice(0, 2).map((l) => <LabelChip key={l.id} label={l} />)}
        </div>
        {issue.estimate != null && (
          <span className="hidden w-8 shrink-0 text-center text-xs text-muted lg:block">{issue.estimate}</span>
        )}
        <div className="hidden w-24 shrink-0 md:block"><StatusPill status={issue.status} /></div>
        <div className="w-6 shrink-0"><PriorityIcon priority={issue.priority} /></div>
        <div className="hidden w-20 shrink-0 md:block">
          {issue.due_date ? <DueBadge due={issue.due_date} isOverdue={issue.is_overdue} /> : null}
        </div>
        <div className="hidden w-24 shrink-0 text-right text-xs text-muted lg:block">{relativeTime(issue.updated_at)}</div>
        <div className="w-6 shrink-0">
          {issue.assignee ? <Avatar user={issue.assignee} size={22} /> : (
            <span className="inline-block h-[22px] w-[22px] rounded-full border border-dashed" title="Unassigned" />
          )}
        </div>
      </Link>
    </div>
  );
}
