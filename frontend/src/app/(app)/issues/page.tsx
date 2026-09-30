"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { X, Search } from "lucide-react";
import { useIssues, useMeta, useTeam, useProjects } from "@/lib/queries";
import { CenterSpinner, EmptyState } from "@/components/ui/misc";
import { IssueRow } from "@/components/IssueRow";
import { useState, useEffect } from "react";

/**
 * Workspace-wide issue list driven entirely by the URL, so every dashboard
 * number can deep-link into exactly the set of issues it counts
 * (e.g. /issues?overdue=true, /issues?status=3).
 */
function IssuesPageInner() {
  const params = useSearchParams();
  const router = useRouter();
  const { data: meta } = useMeta();
  const { data: team } = useTeam();
  const { data: projects } = useProjects();

  const status = params.get("status") || "";
  const priority = params.get("priority") || "";
  const assignee = params.get("assignee") || "";
  const project = params.get("project") || "";
  const overdue = params.get("overdue") === "true";
  const mine = params.get("mine") === "true";
  const done = params.get("done") === "true";
  const title = params.get("title") || "Issues";

  const [search, setSearch] = useState(params.get("search") || "");
  const [offset, setOffset] = useState(0);
  const limit = 40;

  useEffect(() => setOffset(0), [status, priority, assignee, project, overdue, mine, search]);

  // "Done this week" is the one count that isn't an open-issue filter.
  const doneStatusIds = (meta?.statuses || []).filter((s) => s.category === "done").map((s) => s.id);
  const openStatusIds = (meta?.statuses || []).filter((s) => s.category !== "done").map((s) => s.id);

  const effectiveStatus = status
    ? status
    : done
      ? doneStatusIds.join(",")
      : overdue || mine || priority
        ? openStatusIds.join(",")
        : "";

  const { data, isLoading } = useIssues({
    status: effectiveStatus || undefined,
    priority: priority || undefined,
    assignee: assignee || undefined,
    project: project || undefined,
    overdue: overdue || undefined,
    mine: mine || undefined,
    search: search || undefined,
    sort: "updated", order: "desc", limit, offset,
  });

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(params.toString());
    if (value) next.set(key, value);
    else next.delete(key);
    next.delete("title");
    router.replace(`/issues?${next.toString()}`);
  }

  const filtersActive = !!(status || priority || assignee || project || overdue || mine || done);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b bg-surface px-5 pt-4">
        <h1 className="text-lg font-semibold tracking-tight">{title}</h1>
        <p className="mt-0.5 text-sm text-muted">
          {data ? `${data.total} ${data.total === 1 ? "issue" : "issues"}` : " "}
        </p>

        <div className="mt-3 flex flex-wrap items-center gap-2 pb-3">
          <div className="flex h-8 min-w-[180px] flex-1 items-center gap-2 rounded-lg border px-2">
            <Search size={14} className="text-muted" />
            <input value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Search…" className="w-full bg-transparent text-sm outline-none" />
          </div>
          <select className="input h-8 w-auto" value={project} onChange={(e) => setParam("project", e.target.value)}>
            <option value="">All projects</option>
            {projects?.map((p) => <option key={p.id} value={p.key}>{p.key} · {p.name}</option>)}
          </select>
          <select className="input h-8 w-auto" value={status} onChange={(e) => setParam("status", e.target.value)}>
            <option value="">All statuses</option>
            {meta?.statuses.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <select className="input h-8 w-auto" value={priority} onChange={(e) => setParam("priority", e.target.value)}>
            <option value="">All priorities</option>
            {meta?.priorities.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <select className="input h-8 w-auto" value={assignee} onChange={(e) => setParam("assignee", e.target.value)}>
            <option value="">All assignees</option>
            {team?.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
          </select>
          {filtersActive && (
            <button className="btn-ghost h-8 px-2 text-xs" onClick={() => router.replace("/issues")}>
              <X size={13} /> Clear filters
            </button>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {isLoading ? <CenterSpinner /> : !data || data.items.length === 0 ? (
          <div className="p-6">
            <EmptyState title="Nothing here" description="No issues match these filters." />
          </div>
        ) : (
          <div className="card m-5 overflow-hidden">
            {data.items.map((i) => <IssueRow key={i.id} issue={i} showProject />)}
          </div>
        )}
      </div>

      {data && data.total > limit && (
        <div className="flex items-center justify-between border-t bg-surface px-5 py-2 text-sm">
          <span className="text-muted">
            {offset + 1}–{Math.min(offset + limit, data.total)} of {data.total}
          </span>
          <div className="flex gap-2">
            <button className="btn-outline h-8" disabled={offset === 0}
              onClick={() => setOffset((o) => Math.max(0, o - limit))}>Previous</button>
            <button className="btn-outline h-8" disabled={offset + limit >= data.total}
              onClick={() => setOffset((o) => o + limit)}>Next</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function IssuesPage() {
  return (
    <Suspense fallback={<CenterSpinner />}>
      <IssuesPageInner />
    </Suspense>
  );
}
