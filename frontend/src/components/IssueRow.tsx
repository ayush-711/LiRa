"use client";

import Link from "next/link";
import type { IssueSummary } from "@/lib/types";
import { Avatar } from "@/components/ui/Avatar";
import { TypeIcon, PriorityIcon, StatusPill, LabelChip, DueBadge } from "@/components/ui/meta";
import { relativeTime } from "@/lib/utils";

export function IssueRow({ issue, showProject }: { issue: IssueSummary; showProject?: boolean }) {
  return (
    <Link href={`/issues/${issue.key}`}
      className="flex items-center gap-3 border-b px-3 py-2 text-sm hover:bg-surface-2">
      <TypeIcon type={issue.type} />
      <span className="w-16 shrink-0 font-mono text-xs text-muted">{issue.key}</span>
      <span className="min-w-0 flex-1 truncate">{issue.title}</span>
      <div className="hidden shrink-0 items-center gap-1 md:flex">
        {issue.labels.slice(0, 2).map((l) => <LabelChip key={l.id} label={l} />)}
      </div>
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
  );
}
