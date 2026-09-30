"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Modal } from "@/components/ui/overlays";
import { Spinner } from "@/components/ui/misc";
import { useToast } from "@/lib/toast";
import type { Project } from "@/lib/types";

export function CreateProjectModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const router = useRouter();
  const toast = useToast();
  const [name, setName] = useState("");
  const [key, setKey] = useState("");
  const [description, setDescription] = useState("");
  const [keyEdited, setKeyEdited] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function onName(v: string) {
    setName(v);
    if (!keyEdited) {
      setKey(v.replace(/[^A-Za-z]/g, "").slice(0, 4).toUpperCase());
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const project = await api<Project>("/projects", {
        method: "POST",
        body: { name, key, description: description || null },
      });
      qc.invalidateQueries({ queryKey: ["projects"] });
      toast(`Created ${project.name}`);
      onClose();
      setName(""); setKey(""); setDescription(""); setKeyEdited(false);
      router.push(`/projects/${project.key}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create project");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Create project">
      <form onSubmit={submit} className="space-y-3">
        {error && <div className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400">{error}</div>}
        <div>
          <label className="label-text">Name</label>
          <input required autoFocus className="input mt-1" value={name}
            onChange={(e) => onName(e.target.value)} placeholder="Document AI" />
        </div>
        <div>
          <label className="label-text">Key</label>
          <input required className="input mt-1 font-mono uppercase" value={key} maxLength={10}
            onChange={(e) => { setKeyEdited(true); setKey(e.target.value.toUpperCase()); }} placeholder="DOC" />
          <p className="mt-1 text-xs text-muted">Used for issue IDs, e.g. {key || "DOC"}-124</p>
        </div>
        <div>
          <label className="label-text">Description</label>
          <textarea className="input mt-1 h-20 py-2" value={description}
            onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" className="btn-outline" onClick={onClose}>Cancel</button>
          <button className="btn-primary" disabled={loading}>
            {loading ? <Spinner className="text-white" /> : "Create project"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
