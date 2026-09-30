"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Trash2, UserPlus, Archive, ArchiveRestore } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useProject, useProjectMembers, useTeam } from "@/lib/queries";
import { useAuth } from "@/lib/auth";
import { useToast } from "@/lib/toast";
import { CenterSpinner, EmptyState } from "@/components/ui/misc";
import { Avatar } from "@/components/ui/Avatar";

export default function ProjectSettingsPage() {
  const { key } = useParams<{ key: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const toast = useToast();
  const { user } = useAuth();
  const { data: project } = useProject(key);
  const { data: members } = useProjectMembers(key);
  const { data: team } = useTeam();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState("active");
  const [startDate, setStartDate] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [addUserId, setAddUserId] = useState<number | "">("");
  const [addRole, setAddRole] = useState<"member" | "manager">("member");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (project) {
      setName(project.name);
      setDescription(project.description || "");
      setStatus(project.status);
      setStartDate(project.start_date || "");
      setTargetDate(project.target_date || "");
    }
  }, [project]);

  if (!project) return <CenterSpinner />;

  // Admins can always manage a project, even if they aren't a member of it —
  // this mirrors the server-side rule (permissions.can_manage_project).
  const isAdmin = user?.role === "admin";
  const canManage = isAdmin || project.my_role === "manager";
  const archived = project.status === "archived";

  async function save() {
    setSaving(true);
    try {
      await api(`/projects/${key}`, {
        method: "PATCH",
        body: {
          name, description: description || null, status,
          start_date: startDate || null, target_date: targetDate || null,
        },
      });
      qc.invalidateQueries({ queryKey: ["project", key] });
      qc.invalidateQueries({ queryKey: ["projects"] });
      toast("Project updated");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Failed", "error");
    } finally {
      setSaving(false);
    }
  }

  async function addMember() {
    if (!addUserId) return;
    try {
      await api(`/projects/${key}/members`, {
        method: "POST", body: { user_id: addUserId, role: addRole },
      });
      qc.invalidateQueries({ queryKey: ["members", key] });
      qc.invalidateQueries({ queryKey: ["user-projects"] });
      setAddUserId("");
      toast("Member added");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Failed", "error");
    }
  }

  async function setMemberRole(userId: number, role: "member" | "manager") {
    try {
      await api(`/projects/${key}/members/${userId}`, {
        method: "PATCH", body: { user_id: userId, role },
      });
      qc.invalidateQueries({ queryKey: ["members", key] });
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Failed", "error");
    }
  }

  async function removeMember(userId: number) {
    try {
      await api(`/projects/${key}/members/${userId}`, { method: "DELETE" });
      qc.invalidateQueries({ queryKey: ["members", key] });
      qc.invalidateQueries({ queryKey: ["user-projects"] });
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Failed", "error");
    }
  }

  async function toggleArchive() {
    const restoring = archived;
    try {
      await api(`/projects/${key}/${restoring ? "unarchive" : "archive"}`, { method: "POST" });
      qc.invalidateQueries();
      toast(restoring ? "Project restored" : 'Project archived — find it under "Show archived"');
      if (!restoring) router.push("/projects");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Failed", "error");
    }
  }

  const memberIds = new Set(members?.map((m) => m.user.id));
  const addable = (team || []).filter((u) => u.is_active && !memberIds.has(u.id));

  if (!canManage) {
    return (
      <div className="p-6">
        <EmptyState
          title="Read-only"
          description="Only this project's managers and administrators can change its settings."
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      {/* Members first — it's the most-used control here */}
      <section className="card p-5">
        <div className="mb-1 flex items-center gap-2">
          <UserPlus size={16} className="text-brand" />
          <h2 className="text-sm font-semibold">Members</h2>
        </div>
        <p className="mb-3 text-sm text-muted">
          Members can create and work on issues in this project, and can be assigned to them.
        </p>

        <div className="space-y-1.5">
          {members?.map((m) => (
            <div key={m.id} className="flex items-center gap-3 rounded-lg border px-3 py-2">
              <Avatar user={m.user} size={28} />
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium">{m.user.name}</div>
                <div className="truncate text-xs text-muted">{m.user.email}</div>
              </div>
              <select
                className="input h-8 w-auto text-xs"
                value={m.role}
                onChange={(e) => setMemberRole(m.user.id, e.target.value as "member" | "manager")}
                aria-label={`Role for ${m.user.name}`}
              >
                <option value="member">Member</option>
                <option value="manager">Manager</option>
              </select>
              <button onClick={() => removeMember(m.user.id)}
                className="text-muted hover:text-red-600" aria-label={`Remove ${m.user.name}`}>
                <Trash2 size={15} />
              </button>
            </div>
          ))}
          {members?.length === 0 && (
            <p className="rounded-lg border border-dashed px-3 py-4 text-center text-sm text-muted">
              No members yet — add someone below.
            </p>
          )}
        </div>

        <div className="mt-3 flex flex-wrap gap-2 border-t pt-3">
          <select className="input h-9 min-w-[180px] flex-1" value={addUserId}
            onChange={(e) => setAddUserId(Number(e.target.value) || "")} aria-label="Person to add">
            <option value="">Add a person…</option>
            {addable.map((u) => <option key={u.id} value={u.id}>{u.name} · {u.email}</option>)}
          </select>
          <select className="input h-9 w-auto" value={addRole}
            onChange={(e) => setAddRole(e.target.value as "member" | "manager")} aria-label="Role to grant">
            <option value="member">Member</option>
            <option value="manager">Manager</option>
          </select>
          <button className="btn-primary" onClick={addMember} disabled={!addUserId}>
            <UserPlus size={15} /> Add
          </button>
        </div>
        {addable.length === 0 && (
          <p className="mt-2 text-xs text-muted">
            Everyone on the team is already a member. Invite more people from the Team page.
          </p>
        )}
      </section>

      {/* Details */}
      <section className="card p-5">
        <h2 className="mb-3 text-sm font-semibold">Project details</h2>
        <div className="space-y-3">
          <div>
            <label className="label-text" htmlFor="p-name">Name</label>
            <input id="p-name" className="input mt-1" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label className="label-text" htmlFor="p-desc">Description</label>
            <textarea id="p-desc" className="input mt-1 h-20 py-2" value={description}
              onChange={(e) => setDescription(e.target.value)} />
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <label className="label-text" htmlFor="p-status">Status</label>
              <select id="p-status" className="input mt-1" value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="planning">Planning</option>
                <option value="active">Active</option>
                <option value="completed">Completed</option>
              </select>
            </div>
            <div>
              <label className="label-text" htmlFor="p-start">Start date</label>
              <input id="p-start" type="date" className="input mt-1" value={startDate}
                onChange={(e) => setStartDate(e.target.value)} />
            </div>
            <div>
              <label className="label-text" htmlFor="p-target">Target date</label>
              <input id="p-target" type="date" className="input mt-1" value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)} />
            </div>
          </div>
          <button className="btn-primary" onClick={save} disabled={saving}>
            {saving ? "Saving…" : "Save changes"}
          </button>
        </div>
      </section>

      {/* Archive */}
      <section className="card p-5">
        <h2 className="mb-1 text-sm font-semibold">
          {archived ? "Restore project" : "Archive project"}
        </h2>
        <p className="mb-3 text-sm text-muted">
          {archived
            ? "This project is archived. Restoring makes it active again."
            : "Archiving hides the project from active lists. Issues are preserved and it can be restored."}
        </p>
        <button
          className={archived ? "btn-outline" : "btn-outline text-red-600 hover:bg-red-500/10"}
          onClick={toggleArchive}
          disabled={archived && !isAdmin}
        >
          {archived ? <><ArchiveRestore size={15} /> Restore project</> : <><Archive size={15} /> Archive project</>}
        </button>
        {archived && !isAdmin && (
          <p className="mt-2 text-xs text-muted">Only an administrator can restore a project.</p>
        )}
      </section>
    </div>
  );
}
