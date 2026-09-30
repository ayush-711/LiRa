"use client";

import Link from "next/link";
import { usePathname, useParams } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { useProject } from "@/lib/queries";
import { cn } from "@/lib/utils";

const TABS = [
  { seg: "", label: "Overview" },
  { seg: "board", label: "Board" },
  { seg: "issues", label: "Issues" },
  { seg: "activity", label: "Activity" },
  { seg: "settings", label: "Settings" },
];

export default function ProjectLayout({ children }: { children: React.ReactNode }) {
  const { key } = useParams<{ key: string }>();
  const pathname = usePathname();
  const { data: project } = useProject(key);
  const base = `/projects/${key}`;

  return (
    <div className="flex h-full flex-col">
      <div className="border-b bg-surface px-5 pt-3">
        <div className="flex items-center gap-1 text-xs text-muted">
          <Link href="/projects" className="hover:text-fg">Projects</Link>
          <ChevronRight size={12} />
          <span className="text-fg-subtle">{project?.name || key}</span>
        </div>
        <div className="mt-1 flex items-center gap-2">
          <span className="font-mono text-xs font-semibold text-brand">{key}</span>
          <h1 className="text-base font-semibold">{project?.name}</h1>
        </div>
        <nav className="mt-2 flex gap-1 overflow-x-auto">
          {TABS.map((t) => {
            const href = t.seg ? `${base}/${t.seg}` : base;
            const active = t.seg
              ? pathname.startsWith(href)
              : pathname === base;
            return (
              <Link key={t.seg} href={href}
                className={cn(
                  "border-b-2 px-3 py-1.5 text-sm",
                  active ? "border-brand font-medium text-brand" : "border-transparent text-fg-subtle hover:text-fg"
                )}>
                {t.label}
              </Link>
            );
          })}
        </nav>
      </div>
      <div className="min-h-0 flex-1 overflow-hidden">{children}</div>
    </div>
  );
}
