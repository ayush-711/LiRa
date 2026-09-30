"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useProjects } from "@/lib/queries";
import { useToast } from "@/lib/toast";
import { Spinner } from "@/components/ui/misc";
import { useState } from "react";

interface Membership {
  project_id: number;
  key: string;
  name: string;
  role: "manager" | "member";
  status: string;
}

/**
 * Per-person project access: which projects this user belongs to, with the
 * ability to grant or revoke from the Team page. The same membership is
 * editable from inside a project — both paths hit the same endpoints.
 */
export function ProjectAccess({ userId, canManage }: { userId: number; canManage: boolean }) {
  const qc = useQueryClient();
  const toast = useToast();
  const { data: allProjects } = useProjects();
  const [busy, setBusy] = useState(false);

  const { data: memberships, isLoading } = useQuery({
    queryKey: ["user-projects", userId],
    queryFn: () => api<Membership[]>(`/users/${userId}/projects`),
  });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["user-projects", userId] });
    qc.invalidateQueries({ queryKey: ["members"] });
  };

  async function grant(projectKey: string) {
    setBusy(true);
    try {
      await api(`/projects/${projectKey}/members`, {
        method: "POST",
        body: { user_id: userId, role: "member" },
      });
      refresh();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Couldn't grant access", "error");
    } finally {
      setBusy(false);
    }
  }

  async function revoke(projectKey: string) {
    setBusy(true);
    try {
      await api(`/projects/${projectKey}/members/${userId}`, { method: "DELETE" });
      refresh();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Couldn't remove access", "error");
    } finally {
      setBusy(false);
    }
  }

  async function setRole(projectKey: string, role: "manager" | "member") {
    setBusy(true);
    try {
      await api(`/projects/${projectKey}/members/${userId}`, {
        method: "PATCH",
        body: { user_id: userId, role },
      });
      refresh();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Couldn't change role", "error");
    } finally {
      setBusy(false);
    }
  }

  if (isLoading) return <div className="py-2"><Spinner /></div>;

  const joinedIds = new Set((memberships || []).map((m) => m.project_id));
  const available = (allProjects || []).filter((p) => !joinedIds.has(p.id));

  return (
    <div className="space-y-2">
      {memberships && memberships.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {memberships.map((m) => (
            <span key={m.project_id}
              className="inline-flex items-center gap-1.5 rounded-md border bg-surface px-2 py-1 text-xs">
              <span className="font-mono font-semibold text-brand">{m.key}</span>
              <span className="text-fg-subtle">{m.name}</span>
              {canManage ? (
                <select
                  value={m.role}
                  disabled={busy}
                  onChange={(e) => setRole(m.key, e.target.value as "manager" | "member")}
                  className="ml-1 rounded border bg-surface-2 px-1 py-0.5 text-[11px]"
                  aria-label={`Role in ${m.key}`}
                >
                  <option value="member">Member</option>
                  <option value="manager">Manager</option>
                </select>
              ) : (
                <span className="text-muted capitalize">{m.role}</span>
              )}
              {canManage && (
                <button onClick={() => revoke(m.key)} disabled={busy}
                  className="text-muted hover:text-red-600" aria-label={`Remove from ${m.key}`}>
                  <X size={12} />
                </button>
              )}
            </span>
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted">No project access yet.</p>
      )}

      {canManage && available.length > 0 && (
        <select
          value=""
          disabled={busy}
          onChange={(e) => e.target.value && grant(e.target.value)}
          className="input h-8 w-auto text-xs"
          aria-label="Grant project access"
        >
          <option value="">+ Give access to a project…</option>
          {available.map((p) => (
            <option key={p.id} value={p.key}>{p.key} · {p.name}</option>
          ))}
        </select>
      )}
    </div>
  );
}
