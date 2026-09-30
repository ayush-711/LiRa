"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import {
  FolderKanban, Plus, MoreHorizontal, Archive, ArchiveRestore,
  Settings, LayoutGrid, Users,
} from "lucide-react";
import { useProjects, useDashboard } from "@/lib/queries";
import { useAuth } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";
import { useToast } from "@/lib/toast";
import { CenterSpinner, EmptyState, Menu, MenuItem } from "@/components/ui/misc";
import { CreateProjectModal } from "@/components/CreateProjectModal";
import { cn } from "@/lib/utils";
import type { Project } from "@/lib/types";

export default function ProjectsPage() {
  const [showArchived, setShowArchived] = useState(false);
  const { data: projects, isLoading } = useProjects(showArchived);
  const { data: dashboard } = useDashboard();
  const { user } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const router = useRouter();
  const [createOpen, setCreateOpen] = useState(false);

  const statsByKey = new Map((dashboard?.projects || []).map((p) => [p.key, p]));
  const isAdmin = user?.role === "admin";

  async function act(path: string, label: string) {
    try {
      await api(path, { method: "POST" });
      qc.invalidateQueries();
      toast(label);
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Action failed", "error");
    }
  }

  const visible = projects || [];
  const archivedCount = visible.filter((p) => p.status === "archived").length;

  return (
    <div className="mx-auto max-w-6xl p-6">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Projects</h1>
          <p className="mt-0.5 text-sm text-muted">
            {visible.length} {visible.length === 1 ? "project" : "projects"}
            {showArchived && archivedCount > 0 && ` · ${archivedCount} archived`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowArchived((v) => !v)}
            className={cn("btn-outline h-9 text-xs", showArchived && "border-brand text-brand")}
          >
            <Archive size={14} /> {showArchived ? "Hide archived" : "Show archived"}
          </button>
          {isAdmin && (
            <button className="btn-primary px-4 font-semibold" onClick={() => setCreateOpen(true)}>
              <Plus size={17} strokeWidth={2.6} /> New project
            </button>
          )}
        </div>
      </div>

      {isLoading ? (
        <CenterSpinner />
      ) : visible.length === 0 ? (
        <EmptyState
          icon={<FolderKanban size={34} strokeWidth={1.4} />}
          title="No projects yet"
          description={isAdmin
            ? "Create your first project to start tracking work."
            : "An administrator hasn't created any projects yet."}
          action={isAdmin ? (
            <button className="btn-primary px-4" onClick={() => setCreateOpen(true)}>
              <Plus size={16} /> New project
            </button>
          ) : undefined}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {visible.map((p) => (
            <ProjectCard
              key={p.id}
              project={p}
              stats={statsByKey.get(p.key)}
              isAdmin={!!isAdmin}
              onArchive={() => act(`/projects/${p.key}/archive`, `Archived ${p.key} — find it under "Show archived"`)}
              onRestore={() => act(`/projects/${p.key}/unarchive`, `Restored ${p.key}`)}
              onSettings={() => router.push(`/projects/${p.key}/settings`)}
            />
          ))}
        </div>
      )}

      <CreateProjectModal open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}

function ProjectCard({
  project: p, stats, isAdmin, onArchive, onRestore, onSettings,
}: {
  project: Project;
  stats?: { total_issues: number; done_issues: number; completion: number };
  isAdmin: boolean;
  onArchive: () => void;
  onRestore: () => void;
  onSettings: () => void;
}) {
  const archived = p.status === "archived";
  const completion = stats?.completion ?? 0;
  const canManage = isAdmin || p.my_role === "manager";

  return (
    <div
      className={cn(
        "group relative flex flex-col rounded-xl border bg-surface p-5 shadow-soft transition-all",
        archived ? "opacity-60" : "hover:-translate-y-0.5 hover:border-brand/40 hover:shadow-pop"
      )}
    >
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-soft text-brand">
          <LayoutGrid size={17} />
        </span>
        <div className="min-w-0 flex-1">
          <span className="font-mono text-[11px] font-semibold tracking-wider text-brand">{p.key}</span>
          {/* The stretched link makes the whole card clickable without nesting
              interactive elements inside an <a>. */}
          <h3 className="truncate font-semibold leading-tight">
            <Link href={`/projects/${p.key}`} className="after:absolute after:inset-0 after:content-['']">
              {p.name}
            </Link>
          </h3>
        </div>

        {canManage && (
          <div className="relative z-10 -mr-1 -mt-1 shrink-0">
            <Menu
              trigger={
                <span className="flex h-7 w-7 items-center justify-center rounded-md text-muted transition-colors hover:bg-surface-2 hover:text-fg">
                  <MoreHorizontal size={16} />
                </span>
              }
            >
              {(close) => (
                <>
                  <MenuItem onClick={() => { close(); onSettings(); }}>
                    <Settings size={14} /> Project settings
                  </MenuItem>
                  {archived ? (
                    isAdmin ? (
                      <MenuItem onClick={() => { close(); onRestore(); }}>
                        <ArchiveRestore size={14} /> Restore project
                      </MenuItem>
                    ) : null
                  ) : (
                    <MenuItem danger onClick={() => { close(); onArchive(); }}>
                      <Archive size={14} /> Archive project
                    </MenuItem>
                  )}
                </>
              )}
            </Menu>
          </div>
        )}
      </div>

      <p className="mt-3 line-clamp-2 min-h-[2.5rem] text-sm text-muted">
        {p.description || "No description."}
      </p>

      <div className="mt-4 space-y-2">
        <div className="flex items-baseline justify-between text-xs">
          <span>
            <span className="font-medium text-fg">{stats?.done_issues ?? 0}</span>
            <span className="text-muted"> / {stats?.total_issues ?? 0} done</span>
          </span>
          <span className="font-medium tabular-nums text-fg-subtle">{completion}%</span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-surface-2">
          <div className="h-full rounded-full bg-brand transition-all" style={{ width: `${completion}%` }} />
        </div>
      </div>

      <div className="mt-4 flex items-center gap-3 border-t pt-3 text-xs text-muted">
        {archived ? (
          <span className="inline-flex items-center gap-1.5"><Archive size={12} /> Archived</span>
        ) : (
          <>
            <Link href={`/projects/${p.key}/board`}
              className="relative z-10 inline-flex items-center gap-1.5 hover:text-brand">
              <LayoutGrid size={12} /> Board
            </Link>
            <Link href={`/projects/${p.key}/settings`}
              className="relative z-10 inline-flex items-center gap-1.5 hover:text-brand">
              <Users size={12} /> Members
            </Link>
            {p.my_role && <span className="ml-auto capitalize">{p.my_role}</span>}
          </>
        )}
      </div>
    </div>
  );
}
