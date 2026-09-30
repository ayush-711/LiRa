"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useMeta, useProjects, useProjectMembers } from "@/lib/queries";
import { Modal } from "@/components/ui/overlays";
import { Spinner } from "@/components/ui/misc";
import { LabelPicker } from "@/components/LabelPicker";
import { useToast } from "@/lib/toast";
import type { IssueDetail } from "@/lib/types";

export function CreateIssueModal({
  open,
  onClose,
  defaultProjectKey,
  defaultStatusId,
  parentId,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  defaultProjectKey?: string;
  defaultStatusId?: number;
  parentId?: number;
  onCreated?: (issue: IssueDetail) => void;
}) {
  const { data: projects } = useProjects();
  const { data: meta } = useMeta();
  const qc = useQueryClient();
  const router = useRouter();
  const toast = useToast();

  const [projectKey, setProjectKey] = useState(defaultProjectKey || "");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [typeId, setTypeId] = useState<number | "">("");
  const [priorityId, setPriorityId] = useState<number | "">("");
  const [assigneeId, setAssigneeId] = useState<number | "">("");
  const [dueDate, setDueDate] = useState("");
  const [labelIds, setLabelIds] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const project = projects?.find((p) => p.key === projectKey);
  const { data: members } = useProjectMembers(project?.key || "");

  useEffect(() => {
    if (open) {
      setProjectKey(defaultProjectKey || "");
      setTitle("");
      setDescription("");
      setTypeId("");
      setPriorityId("");
      setAssigneeId("");
      setDueDate("");
      setLabelIds([]);
      setError(null);
    }
  }, [open, defaultProjectKey]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!project) {
      setError("Please choose a project");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const issue = await api<IssueDetail>("/issues", {
        method: "POST",
        body: {
          project_id: project.id,
          title,
          description: description || null,
          type_id: typeId || undefined,
          priority_id: priorityId || undefined,
          status_id: defaultStatusId || undefined,
          assignee_id: assigneeId || undefined,
          due_date: dueDate || undefined,
          parent_id: parentId,
          label_ids: labelIds.length ? labelIds : undefined,
        },
      });
      qc.invalidateQueries();
      toast(`Created ${issue.key}`);
      onClose();
      if (onCreated) onCreated(issue);
      else router.push(`/issues/${issue.key}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create issue");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Create issue" wide>
      <form onSubmit={submit} className="space-y-3">
        {error && <div className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400">{error}</div>}

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label-text" htmlFor="ci-project">Project</label>
            <select id="ci-project" className="input mt-1" value={projectKey} onChange={(e) => setProjectKey(e.target.value)} required>
              <option value="">Select…</option>
              {projects?.map((p) => (
                <option key={p.id} value={p.key}>{p.key} · {p.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label-text" htmlFor="ci-type">Type</label>
            <select id="ci-type" className="input mt-1" value={typeId} onChange={(e) => setTypeId(Number(e.target.value) || "")}>
              <option value="">Task (default)</option>
              {meta?.types.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </div>
        </div>

        <div>
          <label className="label-text" htmlFor="ci-title">Title</label>
          <input id="ci-title" required autoFocus className="input mt-1" value={title}
            onChange={(e) => setTitle(e.target.value)} placeholder="What needs to be done?" />
        </div>

        <div>
          <label className="label-text" htmlFor="ci-description">Description</label>
          <textarea id="ci-description" className="input mt-1 h-24 py-2" value={description}
            onChange={(e) => setDescription(e.target.value)} placeholder="Add more detail (Markdown supported)…" />
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="label-text" htmlFor="ci-priority">Priority</label>
            <select id="ci-priority" className="input mt-1" value={priorityId} onChange={(e) => setPriorityId(Number(e.target.value) || "")}>
              <option value="">None</option>
              {meta?.priorities.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label-text" htmlFor="ci-assignee">Assignee</label>
            <select id="ci-assignee" className="input mt-1" value={assigneeId} onChange={(e) => setAssigneeId(Number(e.target.value) || "")}>
              <option value="">Unassigned</option>
              {members?.map((m) => <option key={m.user.id} value={m.user.id}>{m.user.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label-text" htmlFor="ci-due">Due date</label>
            <input id="ci-due" type="date" className="input mt-1" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
          </div>
        </div>

        <div>
          <label className="label-text">Labels</label>
          <div className="mt-1.5">
            <LabelPicker value={labelIds} onChange={setLabelIds} />
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-outline" onClick={onClose}>Cancel</button>
          <button className="btn-primary" disabled={loading}>
            {loading ? <Spinner className="text-white" /> : "Create issue"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
