"use client";

import { useState } from "react";
import Link from "next/link";
import {
  FolderKanban, CircleDot, AlertTriangle, Flame, CheckCircle2, ChevronRight,
} from "lucide-react";
import { useDashboard, useMeta } from "@/lib/queries";
import { useAuth } from "@/lib/auth";
import { CenterSpinner } from "@/components/ui/misc";
import { Avatar } from "@/components/ui/Avatar";
import { relativeTime } from "@/lib/utils";

const PREVIEW = 5;

/** Clickable metric — every number on this page opens the issues behind it. */
function Stat({
  icon, label, value, tone, href,
}: {
  icon: React.ReactNode; label: string; value: number; tone?: string; href: string;
}) {
  return (
    <Link
      href={href}
      className="card group flex items-center gap-3 p-3.5 transition-all hover:-translate-y-0.5 hover:border-brand/40 hover:shadow-pop"
    >
      <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${tone || "bg-surface-2 text-fg-subtle"}`}>
        {icon}
      </div>
      <div className="min-w-0">
        <div className="text-xl font-semibold leading-tight">{value}</div>
        <div className="truncate text-xs text-muted">{label}</div>
      </div>
      <ChevronRight size={15} className="ml-auto shrink-0 text-muted opacity-0 transition-opacity group-hover:opacity-100" />
    </Link>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const { data, isLoading } = useDashboard();
  const { data: meta } = useMeta();
  const [showAllProjects, setShowAllProjects] = useState(false);

  if (isLoading || !data) return <CenterSpinner />;

  // Resolve ids from reference data rather than hard-coding them.
  const urgentIds = (meta?.priorities || []).filter((p) => p.rank >= 4).map((p) => p.id).join(",");

  const projects = showAllProjects ? data.projects : data.projects.slice(0, PREVIEW);

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">
          Good to see you, {user?.name.split(" ")[0]}
        </h1>
        <p className="text-sm text-muted">Here's what's happening across your team.</p>
      </div>

      {/* Overview — each tile deep-links to the matching issue list */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <Stat icon={<FolderKanban size={18} />} label="Active projects"
          value={data.overview.active_projects} href="/projects" />
        <Stat icon={<CircleDot size={18} />} label="Open issues"
          value={data.overview.open_issues} href="/issues?title=Open%20issues" />
        <Stat icon={<AlertTriangle size={18} />} label="Overdue"
          value={data.overview.overdue_issues}
          tone="bg-red-500/10 text-red-600 dark:text-red-400"
          href="/issues?overdue=true&title=Overdue%20issues" />
        <Stat icon={<Flame size={18} />} label="Urgent"
          value={data.overview.urgent_issues}
          tone="bg-orange-500/10 text-orange-600 dark:text-orange-400"
          href={`/issues?priority=${urgentIds}&title=Urgent%20issues`} />
        <Stat icon={<CheckCircle2 size={18} />} label="Done this week"
          value={data.overview.completed_recently}
          tone="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
          href="/issues?done=true&title=Recently%20completed" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Projects — most active first */}
        <section className="card p-5">
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="text-sm font-semibold">Projects</h2>
            <span className="text-xs text-muted">most active first</span>
          </div>
          <div className="space-y-1">
            {data.projects.length === 0 && <p className="text-sm text-muted">No projects yet.</p>}
            {projects.map((p) => (
              <Link key={p.id} href={`/projects/${p.key}`}
                className="block rounded-lg p-2 transition-colors hover:bg-surface-2">
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-mono text-[11px] font-semibold text-brand">{p.key}</span>
                  <span className="min-w-0 flex-1 truncate font-medium">{p.name}</span>
                  <span className="shrink-0 text-xs text-muted">{p.done_issues}/{p.total_issues} done</span>
                </div>
                <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-2">
                  <div className="h-full rounded-full bg-brand" style={{ width: `${p.completion}%` }} />
                </div>
              </Link>
            ))}
          </div>
          {data.projects.length > PREVIEW && (
            <button onClick={() => setShowAllProjects((v) => !v)}
              className="mt-3 w-full rounded-lg border py-1.5 text-xs text-fg-subtle transition-colors hover:bg-surface-2">
              {showAllProjects ? "Show less" : `View all ${data.projects.length} projects`}
            </button>
          )}
        </section>

        {/* Recent activity — short preview, full feed on its own page */}
        <section className="card p-5">
          <h2 className="mb-3 text-sm font-semibold">Recent activity</h2>
          <div className="space-y-2.5">
            {data.recent_activity.length === 0 && <p className="text-sm text-muted">No recent activity.</p>}
            {data.recent_activity.slice(0, PREVIEW).map((a) => (
              <div key={a.id} className="flex items-start gap-2 text-sm">
                <Avatar user={a.actor} size={22} />
                <div className="min-w-0">
                  <span className="text-fg-subtle">{a.text}</span>
                  <span className="ml-1 whitespace-nowrap text-xs text-muted">· {relativeTime(a.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
          <Link href="/activity"
            className="mt-3 block rounded-lg border py-1.5 text-center text-xs text-fg-subtle transition-colors hover:bg-surface-2">
            View all activity
          </Link>
        </section>
      </div>

      {/* Throughput — trailing indicator, so it sits last */}
      {data.throughput && data.throughput.length > 0 && (
        <section className="card p-5">
          <div className="mb-3 flex items-baseline gap-2">
            <h2 className="text-sm font-semibold">Throughput</h2>
            <span className="text-xs text-muted">issues completed per week (last 8 weeks)</span>
          </div>
          <Throughput data={data.throughput} />
        </section>
      )}
    </div>
  );
}

/** Simple bar chart — not worth a charting dependency for one visual. */
function Throughput({ data }: { data: { week: string; count: number; points: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.count));
  return (
    <div className="flex h-28 items-end gap-2">
      {data.map((d) => {
        const label = new Date(d.week).toLocaleDateString(undefined, { month: "short", day: "numeric" });
        return (
          <div key={d.week} className="flex flex-1 flex-col items-center gap-1.5">
            <span className="text-xs tabular-nums text-muted">{d.count || ""}</span>
            <div className="w-full rounded-t bg-brand/80 transition-all"
              style={{ height: `${Math.max(2, (d.count / max) * 72)}px` }}
              title={`Week of ${label}: ${d.count} completed${d.points ? `, ${d.points} points` : ""}`} />
            <span className="text-[10px] text-muted">{label}</span>
          </div>
        );
      })}
    </div>
  );
}
