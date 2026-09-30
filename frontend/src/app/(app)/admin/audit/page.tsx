"use client";

import { useState } from "react";
import { useAudit, useTeam } from "@/lib/queries";
import { useAuth } from "@/lib/auth";
import { CenterSpinner, EmptyState } from "@/components/ui/misc";
import { Avatar } from "@/components/ui/Avatar";
import { fullDate } from "@/lib/utils";

const ACTIONS = [
  "login", "login_failed", "invitation.created", "invitation.accepted",
  "user.deactivated", "role.changed", "project.created", "project.archived",
  "project.membership_changed", "issue.created", "issue.archived", "password_reset",
];

export default function AuditPage() {
  const { user } = useAuth();
  const { data: team } = useTeam();
  const [action, setAction] = useState("");
  const [actorId, setActorId] = useState<number | "">("");
  const [offset, setOffset] = useState(0);
  const limit = 50;
  const { data, isLoading } = useAudit({
    action: action || undefined, actor_id: actorId || undefined, limit, offset,
  });

  if (user?.role !== "admin") return <div className="p-5"><EmptyState title="Admins only" /></div>;

  return (
    <div className="mx-auto max-w-4xl space-y-4 p-5">
      <h1 className="text-lg font-semibold">Audit Log</h1>

      <div className="flex flex-wrap gap-2">
        <select className="input h-8 w-auto" value={action} onChange={(e) => { setAction(e.target.value); setOffset(0); }}>
          <option value="">All actions</option>
          {ACTIONS.map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
        <select className="input h-8 w-auto" value={actorId} onChange={(e) => { setActorId(Number(e.target.value) || ""); setOffset(0); }}>
          <option value="">All users</option>
          {team?.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
        </select>
      </div>

      {isLoading ? <CenterSpinner /> : !data || data.items.length === 0 ? (
        <EmptyState title="No audit entries" />
      ) : (
        <div className="card overflow-hidden">
          {data.items.map((e) => (
            <div key={e.id} className="flex items-center gap-3 border-b px-4 py-2 text-sm">
              <Avatar user={e.actor} size={24} />
              <span className="w-40 shrink-0 font-mono text-xs text-fg-subtle">{e.action}</span>
              <span className="min-w-0 flex-1 truncate text-xs text-muted">
                {e.entity_type ? `${e.entity_type}#${e.entity_id ?? ""}` : ""}
                {e.meta ? " " + JSON.stringify(e.meta) : ""}
              </span>
              <span className="shrink-0 text-xs text-muted">{fullDate(e.created_at)}</span>
            </div>
          ))}
        </div>
      )}

      {data && data.total > limit && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted">{offset + 1}–{Math.min(offset + limit, data.total)} of {data.total}</span>
          <div className="flex gap-2">
            <button className="btn-outline h-8" disabled={offset === 0} onClick={() => setOffset((o) => Math.max(0, o - limit))}>Previous</button>
            <button className="btn-outline h-8" disabled={offset + limit >= data.total} onClick={() => setOffset((o) => o + limit)}>Next</button>
          </div>
        </div>
      )}
    </div>
  );
}
