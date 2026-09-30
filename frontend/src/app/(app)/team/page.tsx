"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Mail, Send, ChevronDown, ChevronRight, Clock, X, Copy, Check } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useTeam, useInvitations } from "@/lib/queries";
import { useAuth } from "@/lib/auth";
import { useToast } from "@/lib/toast";
import { CenterSpinner } from "@/components/ui/misc";
import { Avatar } from "@/components/ui/Avatar";
import { ProjectAccess } from "@/components/team/ProjectAccess";
import { ROLE_LABELS, relativeTime, cn } from "@/lib/utils";
import type { GlobalRole } from "@/lib/types";

const ROLES: GlobalRole[] = ["admin", "project_manager", "member", "viewer"];

const ROLE_HELP: Record<GlobalRole, string> = {
  admin: "Full access — manages people, projects and settings",
  project_manager: "Runs the projects they manage",
  member: "Works on issues in projects they belong to",
  viewer: "Read-only across the workspace",
};

export default function TeamPage() {
  const { user } = useAuth();
  const { data: team, isLoading } = useTeam();
  const { data: invitations } = useInvitations();
  const qc = useQueryClient();
  const toast = useToast();

  const isAdmin = user?.role === "admin";
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<GlobalRole>("member");
  const [inviting, setInviting] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [copied, setCopied] = useState<number | null>(null);

  if (isLoading || !team) return <CenterSpinner />;

  async function invite(e: React.FormEvent) {
    e.preventDefault();
    setInviting(true);
    try {
      await api("/invitations", { method: "POST", body: { email, role } });
      qc.invalidateQueries({ queryKey: ["invitations"] });
      setEmail("");
      toast(`Invitation sent to ${email}`);
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Couldn't send invitation", "error");
    } finally {
      setInviting(false);
    }
  }

  async function revoke(id: number) {
    await api(`/invitations/${id}/revoke`, { method: "POST" });
    qc.invalidateQueries({ queryKey: ["invitations"] });
    toast("Invitation revoked");
  }

  async function changeRole(id: number, r: GlobalRole) {
    try {
      await api(`/users/${id}/role`, { method: "PATCH", body: { role: r } });
      qc.invalidateQueries({ queryKey: ["team"] });
      toast("Role updated");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Couldn't change role", "error");
    }
  }

  async function toggleActive(id: number, active: boolean) {
    try {
      await api(`/users/${id}/${active ? "reactivate" : "deactivate"}`, { method: "POST" });
      qc.invalidateQueries({ queryKey: ["team"] });
      toast(active ? "Member reactivated" : "Member deactivated");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Couldn't update member", "error");
    }
  }

  const pending = (invitations || []).filter((i) => i.is_pending);

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Team</h1>
        <p className="mt-0.5 text-sm text-muted">
          {team.length} {team.length === 1 ? "person" : "people"}
          {pending.length > 0 && ` · ${pending.length} pending invitation${pending.length === 1 ? "" : "s"}`}
        </p>
      </div>

      {/* Invite */}
      {isAdmin && (
        <section className="card p-5">
          <div className="mb-1 flex items-center gap-2">
            <Mail size={16} className="text-brand" />
            <h2 className="text-sm font-semibold">Invite a colleague</h2>
          </div>
          <p className="mb-3 text-sm text-muted">
            They'll get an email with a secure link to set their name and password.
            Invitations expire in 72 hours.
          </p>
          <form onSubmit={invite} className="flex flex-wrap gap-2">
            <input
              type="email" required placeholder="colleague@company.com"
              className="input h-9 min-w-[220px] flex-1"
              value={email} onChange={(e) => setEmail(e.target.value)}
              aria-label="Email to invite"
            />
            <select className="input h-9 w-auto" value={role}
              onChange={(e) => setRole(e.target.value as GlobalRole)} aria-label="Role">
              {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
            </select>
            <button className="btn-primary px-4 font-semibold" disabled={inviting}>
              <Send size={15} /> {inviting ? "Sending…" : "Send invite"}
            </button>
          </form>
          <p className="mt-2 text-xs text-muted">{ROLE_HELP[role]}</p>

          {pending.length > 0 && (
            <div className="mt-4 space-y-1.5 border-t pt-3">
              <p className="label-text">Awaiting acceptance</p>
              {pending.map((i) => (
                <div key={i.id} className="flex flex-wrap items-center gap-2 rounded-lg bg-surface-2/60 px-3 py-2 text-sm">
                  <Clock size={13} className="text-muted" />
                  <span className="font-medium">{i.email}</span>
                  <span className="badge bg-surface text-muted">{ROLE_LABELS[i.role]}</span>
                  <span className="text-xs text-muted">expires {relativeTime(i.expires_at)}</span>
                  <button onClick={() => revoke(i.id)}
                    className="ml-auto text-xs text-red-600 hover:underline">
                    Revoke
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* People */}
      <section className="card overflow-hidden">
        <div className="border-b px-5 py-3">
          <h2 className="text-sm font-semibold">People</h2>
        </div>
        {team.map((u) => {
          const isOpen = expanded === u.id;
          const isSelf = u.id === user?.id;
          return (
            <div key={u.id} className="border-b last:border-b-0">
              <div className="flex flex-wrap items-center gap-3 px-5 py-3">
                <button
                  onClick={() => setExpanded(isOpen ? null : u.id)}
                  className="text-muted hover:text-fg"
                  aria-label={isOpen ? "Hide project access" : "Show project access"}
                >
                  {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </button>
                <Avatar user={u} size={34} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{u.name}</span>
                    {isSelf && <span className="badge bg-brand-soft text-brand">You</span>}
                    {!u.is_active && <span className="badge bg-surface-2 text-muted">Deactivated</span>}
                  </div>
                  <div className="truncate text-xs text-muted">{u.email}</div>
                </div>

                <div className="hidden items-center gap-5 text-center text-xs sm:flex">
                  <Stat label="Assigned" value={u.assigned} />
                  <Stat label="In progress" value={u.in_progress} />
                  <Stat label="Overdue" value={u.overdue} tone={u.overdue > 0 ? "text-red-600" : undefined} />
                </div>

                {isAdmin ? (
                  <div className="flex items-center gap-2">
                    <select className="input h-8 w-auto text-xs" value={u.role} disabled={isSelf}
                      onChange={(e) => changeRole(u.id, e.target.value as GlobalRole)}
                      aria-label={`Role for ${u.name}`}>
                      {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
                    </select>
                    {!isSelf && (
                      <button className="btn-outline h-8 text-xs"
                        onClick={() => toggleActive(u.id, !u.is_active)}>
                        {u.is_active ? "Deactivate" : "Reactivate"}
                      </button>
                    )}
                  </div>
                ) : (
                  <span className="text-xs text-fg-subtle">{ROLE_LABELS[u.role]}</span>
                )}
              </div>

              {isOpen && (
                <div className="border-t bg-surface-2/30 px-5 py-3 pl-14">
                  <p className="label-text mb-2">Project access</p>
                  <ProjectAccess userId={u.id} canManage={!!isAdmin} />
                </div>
              )}
            </div>
          );
        })}
      </section>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <div>
      <div className={cn("font-semibold tabular-nums", tone)}>{value}</div>
      <div className="text-[10px] uppercase tracking-wide text-muted">{label}</div>
    </div>
  );
}
