"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Avatar } from "@/components/ui/Avatar";
import { CenterSpinner, EmptyState } from "@/components/ui/misc";
import { relativeTime, fullDate } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { Activity } from "@/lib/types";

const PAGE_SIZES = [10, 20, 50, 100];

interface FeedResponse {
  items: Activity[];
  returned: number;
  total: number;
  max: number;
}

/** Which issue an event belongs to, when we can tell from the stored values. */
function issueKeyFor(a: Activity): string | null {
  if (a.event_type === "issue.created" && a.new_value) return a.new_value;
  return null;
}

export default function ActivityPage() {
  const [limit, setLimit] = useState(20);
  const { data, isLoading } = useQuery({
    queryKey: ["workspace-activity", limit],
    queryFn: () => api<FeedResponse>(`/activity?limit=${limit}`),
  });

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Activity</h1>
          <p className="mt-0.5 text-sm text-muted">
            Everything that's happened across your projects, newest first.
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-muted">Show</span>
          {PAGE_SIZES.map((n) => (
            <button
              key={n}
              onClick={() => setLimit(n)}
              className={cn(
                "rounded-md border px-2.5 py-1 text-xs transition-colors",
                limit === n ? "border-brand bg-brand-soft font-medium text-brand" : "hover:bg-surface-2"
              )}
            >
              {n}
            </button>
          ))}
        </div>
      </div>

      {isLoading || !data ? (
        <CenterSpinner />
      ) : data.items.length === 0 ? (
        <EmptyState title="No activity yet" description="Actions across your projects will show up here." />
      ) : (
        <>
          <div className="card divide-y">
            {data.items.map((a) => {
              const key = issueKeyFor(a);
              const row = (
                <div className="flex items-start gap-3 px-4 py-2.5">
                  <Avatar user={a.actor} size={26} />
                  <span className="min-w-0 flex-1 text-sm text-fg-subtle">{a.text}</span>
                  <span className="shrink-0 text-xs text-muted" title={fullDate(a.created_at)}>
                    {relativeTime(a.created_at)}
                  </span>
                </div>
              );
              return key ? (
                <Link key={a.id} href={`/issues/${key}`} className="block hover:bg-surface-2">
                  {row}
                </Link>
              ) : (
                <div key={a.id}>{row}</div>
              );
            })}
          </div>

          <p className="text-center text-xs text-muted">
            Showing the {data.returned} most recent of {data.total} events
            {data.total > data.max && ` · this feed caps at ${data.max}`}
            {" · "}
            <Link href="/admin/audit" className="text-brand hover:underline">
              the audit log
            </Link>{" "}
            keeps the permanent record
          </p>
        </>
      )}
    </div>
  );
}
