"use client";

import Link from "next/link";
import type { IssueSummary } from "@/lib/types";
import { Avatar } from "@/components/ui/Avatar";
import { TypeIcon, PriorityIcon, LabelChip, DueBadge } from "@/components/ui/meta";

export function IssueCard({ issue, onOpen }: { issue: IssueSummary; onOpen?: (key: string) => void }) {
  const content = (
    <div className="card cursor-pointer space-y-2 p-2.5 hover:border-brand/40">
      <div className="flex items-center gap-1.5 text-xs text-muted">
        <TypeIcon type={issue.type} />
        <span className="font-mono">{issue.key}</span>
        {issue.is_overdue && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-red-500" title="Overdue" />}
      </div>
      <p className="line-clamp-3 text-sm leading-snug">{issue.title}</p>
      {issue.labels.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {issue.labels.slice(0, 3).map((l) => <LabelChip key={l.id} label={l} />)}
        </div>
      )}
      <div className="flex items-center gap-2 pt-0.5">
        <PriorityIcon priority={issue.priority} />
        {issue.due_date && <DueBadge due={issue.due_date} isOverdue={issue.is_overdue} />}
        <div className="ml-auto">
          {issue.assignee ? <Avatar user={issue.assignee} size={20} /> : (
            <span className="inline-block h-5 w-5 rounded-full border border-dashed" title="Unassigned" />
          )}
        </div>
      </div>
    </div>
  );
  if (onOpen) return <div onClick={() => onOpen(issue.key)}>{content}</div>;
  return <Link href={`/issues/${issue.key}`}>{content}</Link>;
}
