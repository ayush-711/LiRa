"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Avatar } from "@/components/ui/Avatar";
import { CenterSpinner, EmptyState } from "@/components/ui/misc";
import { relativeTime, fullDate } from "@/lib/utils";
import type { Activity } from "@/lib/types";

export default function ProjectActivityPage() {
  const { key } = useParams<{ key: string }>();
  const { data, isLoading } = useQuery({
    queryKey: ["project-activity", key],
    queryFn: () => api<Activity[]>(`/projects/${key}/activity?limit=100`),
  });

  if (isLoading) return <CenterSpinner />;

  return (
    <div className="mx-auto max-w-3xl p-5">
      {!data || data.length === 0 ? (
        <EmptyState title="No activity yet" description="Actions in this project will appear here." />
      ) : (
        <div className="card divide-y">
          {data.map((a) => (
            <div key={a.id} className="flex items-center gap-3 px-4 py-2.5 text-sm">
              <Avatar user={a.actor} size={24} />
              <span className="flex-1 text-fg-subtle">{a.text}</span>
              <span className="text-xs text-muted" title={fullDate(a.created_at)}>{relativeTime(a.created_at)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
