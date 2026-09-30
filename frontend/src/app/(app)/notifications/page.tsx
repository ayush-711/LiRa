"use client";

import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck } from "lucide-react";
import { api } from "@/lib/api";
import { useNotifications } from "@/lib/queries";
import { CenterSpinner, EmptyState } from "@/components/ui/misc";
import { Avatar } from "@/components/ui/Avatar";
import { relativeTime, cn } from "@/lib/utils";

export default function NotificationsPage() {
  const { data, isLoading } = useNotifications();
  const qc = useQueryClient();
  const router = useRouter();

  async function markAll() {
    await api("/notifications/read-all", { method: "POST" });
    qc.invalidateQueries({ queryKey: ["notifications"] });
    qc.invalidateQueries({ queryKey: ["unread"] });
  }
  async function open(n: any) {
    if (!n.is_read) {
      await api(`/notifications/${n.id}/read`, { method: "POST" });
      qc.invalidateQueries({ queryKey: ["notifications"] });
      qc.invalidateQueries({ queryKey: ["unread"] });
    }
    if (n.meta?.issue_key) router.push(`/issues/${n.meta.issue_key}`);
  }

  return (
    <div className="mx-auto max-w-2xl space-y-3 p-5">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Notifications</h1>
        {data && data.length > 0 && (
          <button className="btn-outline h-8" onClick={markAll}><CheckCheck size={14} /> Mark all read</button>
        )}
      </div>
      {isLoading ? <CenterSpinner /> : !data || data.length === 0 ? (
        <EmptyState icon={<Bell size={30} />} title="You're all caught up" description="No notifications right now." />
      ) : (
        <div className="card divide-y">
          {data.map((n) => (
            <button key={n.id} onClick={() => open(n)}
              className={cn("flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-surface-2", !n.is_read && "bg-brand-soft/60")}>
              <Avatar user={n.actor} size={30} />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium">{n.title}</p>
                {n.body && <p className="truncate text-sm text-muted">{n.body}</p>}
                <p className="mt-0.5 text-xs text-muted">{relativeTime(n.created_at)}</p>
              </div>
              {!n.is_read && <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-brand" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
