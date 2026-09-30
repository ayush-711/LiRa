"use client";

import { useParams } from "next/navigation";
import { useProject, useProjectStats, useProjectMembers, useIssues } from "@/lib/queries";
import { CenterSpinner } from "@/components/ui/misc";
import { Avatar } from "@/components/ui/Avatar";
import { IssueRow } from "@/components/IssueRow";
import { ROLE_LABELS } from "@/lib/utils";

function StatBox({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <div className="card p-3 text-center">
      <div className={`text-xl font-semibold ${tone || ""}`}>{value}</div>
      <div className="text-xs text-muted">{label}</div>
    </div>
  );
}

export default function ProjectOverview() {
  const { key } = useParams<{ key: string }>();
  const { data: project } = useProject(key);
  const { data: stats } = useProjectStats(key);
  const { data: members } = useProjectMembers(key);
  const { data: recent } = useIssues({ project: key, sort: "updated", limit: 6 });
  const { data: overdue } = useIssues({ project: key, overdue: true, limit: 5 });

  if (!project) return <CenterSpinner />;

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl space-y-5 p-5">
        {project.description && <p className="text-sm text-fg-subtle">{project.description}</p>}

        {stats && (
          <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
            <StatBox label="Total" value={stats.total_issues} />
            <StatBox label="Open" value={stats.open_issues} />
            <StatBox label="In progress" value={stats.in_progress} />
            <StatBox label="Done" value={stats.done} tone="text-emerald-600" />
            <StatBox label="Overdue" value={stats.overdue} tone="text-red-600" />
            <StatBox label="Urgent" value={stats.urgent} tone="text-orange-600" />
          </div>
        )}

        <div className="grid gap-5 lg:grid-cols-3">
          <div className="space-y-5 lg:col-span-2">
            <section className="card">
              <h2 className="border-b px-4 py-2 text-sm font-semibold">Recently updated</h2>
              <div>{recent?.items.map((i) => <IssueRow key={i.id} issue={i} />)}</div>
              {recent?.items.length === 0 && <p className="p-4 text-sm text-muted">No issues yet.</p>}
            </section>
            {overdue && overdue.items.length > 0 && (
              <section className="card">
                <h2 className="border-b px-4 py-2 text-sm font-semibold text-red-600">Overdue</h2>
                <div>{overdue.items.map((i) => <IssueRow key={i.id} issue={i} />)}</div>
              </section>
            )}
          </div>

          <div className="space-y-4">
            <section className="card p-4">
              <h2 className="mb-2 text-sm font-semibold">Details</h2>
              <dl className="space-y-1.5 text-sm">
                <Row label="Status" value={<span className="capitalize">{project.status}</span>} />
                <Row label="Start" value={project.start_date || "—"} />
                <Row label="Target" value={project.target_date || "—"} />
              </dl>
            </section>
            <section className="card p-4">
              <h2 className="mb-2 text-sm font-semibold">Members ({members?.length || 0})</h2>
              <div className="space-y-2">
                {members?.map((m) => (
                  <div key={m.id} className="flex items-center gap-2 text-sm">
                    <Avatar user={m.user} size={24} />
                    <span className="min-w-0 flex-1 truncate">{m.user.name}</span>
                    <span className="text-xs capitalize text-muted">{m.role}</span>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between">
      <dt className="text-muted">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
