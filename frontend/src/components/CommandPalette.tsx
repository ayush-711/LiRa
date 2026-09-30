"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Search, LayoutDashboard, CircleUser, FolderKanban,
  Users, Bell, Settings, Plus, CornerDownLeft,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { IssueSummary } from "@/lib/types";

interface Command {
  id: string;
  label: string;
  icon: React.ReactNode;
  run: () => void;
}

export function CommandPalette({
  open,
  onClose,
  onCreateIssue,
}: {
  open: boolean;
  onClose: () => void;
  onCreateIssue: () => void;
}) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<{ issues: IssueSummary[]; projects: any[]; users: any[] }>({
    issues: [], projects: [], users: [],
  });
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setQuery("");
      setActive(0);
      setResults({ issues: [], projects: [], users: [] });
      setTimeout(() => inputRef.current?.focus(), 10);
    }
  }, [open]);

  useEffect(() => {
    if (!query.trim()) {
      setResults({ issues: [], projects: [], users: [] });
      return;
    }
    const ctrl = new AbortController();
    const t = setTimeout(() => {
      api<{ issues: IssueSummary[]; projects: any[]; users: any[] }>(
        `/search?q=${encodeURIComponent(query)}`, { signal: ctrl.signal }
      ).then(setResults).catch(() => {});
    }, 180);
    return () => { clearTimeout(t); ctrl.abort(); };
  }, [query]);

  const nav = (path: string) => { onClose(); router.push(path); };

  const commands: Command[] = useMemo(() => [
    { id: "create", label: "Create issue", icon: <Plus size={16} />, run: () => { onClose(); onCreateIssue(); } },
    { id: "dashboard", label: "Go to Dashboard", icon: <LayoutDashboard size={16} />, run: () => nav("/dashboard") },
    { id: "my", label: "Go to My Issues", icon: <CircleUser size={16} />, run: () => nav("/my-issues") },
    { id: "projects", label: "Go to Projects", icon: <FolderKanban size={16} />, run: () => nav("/projects") },
    { id: "team", label: "Go to Team", icon: <Users size={16} />, run: () => nav("/team") },
    { id: "notifications", label: "Open Notifications", icon: <Bell size={16} />, run: () => nav("/notifications") },
    { id: "settings", label: "Open Settings", icon: <Settings size={16} />, run: () => nav("/settings") },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], []);

  const hasQuery = query.trim().length > 0;
  const filteredCommands = hasQuery
    ? commands.filter((c) => c.label.toLowerCase().includes(query.toLowerCase()))
    : commands;

  // Build a flat list of selectable rows for keyboard nav.
  type Row = { key: string; render: React.ReactNode; run: () => void };
  const rows: Row[] = [];
  filteredCommands.forEach((c) =>
    rows.push({
      key: `cmd-${c.id}`,
      run: c.run,
      render: (
        <div className="flex items-center gap-2.5">
          <span className="text-muted">{c.icon}</span>
          <span>{c.label}</span>
        </div>
      ),
    })
  );
  results.issues.forEach((i) =>
    rows.push({
      key: `iss-${i.id}`,
      run: () => nav(`/issues/${i.key}`),
      render: (
        <div className="flex items-center gap-2.5">
          <span className="font-mono text-xs text-muted">{i.key}</span>
          <span className="truncate">{i.title}</span>
        </div>
      ),
    })
  );
  results.projects.forEach((p) =>
    rows.push({
      key: `prj-${p.id}`,
      run: () => nav(`/projects/${p.key}`),
      render: (
        <div className="flex items-center gap-2.5">
          <FolderKanban size={16} className="text-muted" />
          <span>{p.key} · {p.name}</span>
        </div>
      ),
    })
  );

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, rows.length - 1)); }
      else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
      else if (e.key === "Enter") { e.preventDefault(); rows[active]?.run(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center bg-black/30 p-4 pt-[12vh]" onMouseDown={onClose}>
      <div className="card w-full max-w-xl overflow-hidden shadow-pop" onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2 border-b px-3">
          <Search size={16} className="text-muted" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => { setQuery(e.target.value); setActive(0); }}
            placeholder="Search issues, projects, people — or run a command…"
            className="h-11 w-full bg-transparent text-sm outline-none placeholder:text-muted"
          />
        </div>
        <div className="max-h-80 overflow-y-auto p-1.5">
          {rows.length === 0 && (
            <div className="px-3 py-6 text-center text-sm text-muted">No results</div>
          )}
          {rows.map((row, i) => (
            <button
              key={row.key}
              onMouseEnter={() => setActive(i)}
              onClick={row.run}
              className={cn(
                "flex w-full items-center rounded-md px-2.5 py-2 text-left text-sm",
                i === active ? "bg-brand-soft text-brand" : "hover:bg-surface-2"
              )}
            >
              <div className="min-w-0 flex-1">{row.render}</div>
              {i === active && <CornerDownLeft size={13} className="ml-2 shrink-0 text-muted" />}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
