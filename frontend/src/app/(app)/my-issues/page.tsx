"use client";

import { useState } from "react";
import Link from "next/link";
import { useMyIssues } from "@/lib/queries";
import { CenterSpinner, EmptyState } from "@/components/ui/misc";
import { Avatar } from "@/components/ui/Avatar";
import { TypeIcon, PriorityIcon, LabelChip, DueBadge } from "@/components/ui/meta";
import { relativeTime } from "@/lib/utils";
import type { IssueSummary, Status } from "@/lib/types";

interface Group {
  status: Status;
  issues: IssueSummary[];
}

export default function MyIssuesPage() {
  const [sort, setSort] = useState("priority");
  const { data, isLoading } = useMyIssues(sort);

  if (isLoading || !data) return <CenterSpinner />;

  const groups = (data.groups || []) as Group[];
  const total = data.total ?? 0;

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">My Issues</h1>
          <p className="mt-0.5 text-sm text-muted">
            {total} {total === 1 ? "issue" : "issues"} assigned to you
          </p>
        </div>
        <select className="input h-8 w-auto" value={sort} onChange={(e) => setSort(e.target.value)}
          aria-label="Sort issues">
          <option value="priority">Sort: Priority</option>
          <option value="due">Sort: Due date</option>
          <option value="updated">Sort: Updated</option>
          <option value="project">Sort: Project</option>
        </select>
      </div>

      {groups.length === 0 ? (
        <EmptyState title="You're all clear" description="No issues are assigned to you right now." />
      ) : (
        groups.map((g) => (
          <section key={g.status.id} className="card overflow-hidden">
            <div className="flex items-center gap-2 border-b bg-surface-2/40 px-4 py-2">
              <span className="h-2 w-2 rounded-full" style={{ background: g.status.color }} />
              <h2 className="text-sm font-semibold">{g.status.name}</h2>
              <span className="text-xs text-muted">{g.issues.length}</span>
            </div>
            <div>
              {g.issues.map((i) => <Row key={i.id} issue={i} />)}
            </div>
          </section>
        ))
      )}
    </div>
  );
}

/**
 * One issue per line. Everything after the title is fixed-width and
 * `whitespace-nowrap` so a long status or label can never wrap and inflate the
 * row height.
 */
function Row({ issue }: { issue: IssueSummary }) {
  return (
    <Link href={`/issues/${issue.key}`}
      className="flex h-10 items-center gap-3 border-b px-4 text-sm transition-colors last:border-b-0 hover:bg-surface-2">
      <TypeIcon type={issue.type} />
      <span className="w-14 shrink-0 font-mono text-xs text-muted">{issue.key}</span>
      <span className="min-w-0 flex-1 truncate">{issue.title}</span>

      <div className="hidden shrink-0 items-center gap-1 lg:flex">
        {issue.labels.slice(0, 2).map((l) => <LabelChip key={l.id} label={l} />)}
      </div>

      <span className="w-5 shrink-0"><PriorityIcon priority={issue.priority} /></span>

      <span className="hidden w-16 shrink-0 whitespace-nowrap text-xs md:block">
        {issue.due_date ? <DueBadge due={issue.due_date} isOverdue={issue.is_overdue} /> : null}
      </span>

      <span className="hidden w-24 shrink-0 whitespace-nowrap text-right text-xs text-muted lg:block">
        {relativeTime(issue.updated_at)}
      </span>

      <span className="w-6 shrink-0">
        {issue.assignee
          ? <Avatar user={issue.assignee} size={20} />
          : <span className="inline-block h-5 w-5 rounded-full border border-dashed" title="Unassigned" />}
      </span>
    </Link>
  );
}
