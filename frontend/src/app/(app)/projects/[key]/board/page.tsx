"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import {
  DndContext, DragOverlay, PointerSensor, useSensor, useSensors,
  closestCorners, type DragStartEvent, type DragEndEvent,
} from "@dnd-kit/core";
import { SortableContext, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Plus } from "lucide-react";
import { useBoard, useProjectMembers, useMeta, useLabels, useProject } from "@/lib/queries";
import { api } from "@/lib/api";
import { useAuth, canWrite } from "@/lib/auth";
import { useToast } from "@/lib/toast";
import { CenterSpinner } from "@/components/ui/misc";
import { IssueCard } from "@/components/IssueCard";
import { CreateIssueModal } from "@/components/CreateIssueModal";
import { Drawer } from "@/components/ui/overlays";
import { IssueDetailView } from "@/components/issue/IssueDetailView";
import type { BoardColumn, IssueSummary } from "@/lib/types";

export default function BoardPage() {
  const { key } = useParams<{ key: string }>();
  const { user } = useAuth();
  const writable = canWrite(user);
  const qc = useQueryClient();
  const toast = useToast();

  const [filters, setFilters] = useState<Record<string, string | number | boolean>>({});
  const { data: board, isLoading } = useBoard(key, filters);
  const { data: members } = useProjectMembers(key);
  const { data: meta } = useMeta();

  const [columns, setColumns] = useState<BoardColumn[]>([]);
  const [activeIssue, setActiveIssue] = useState<IssueSummary | null>(null);
  const [createStatus, setCreateStatus] = useState<number | null>(null);
  const [openIssueKey, setOpenIssueKey] = useState<string | null>(null);

  useEffect(() => { if (board) setColumns(board.columns); }, [board]);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));
  const allIssues = useMemo(() => columns.flatMap((c) => c.issues), [columns]);

  function findColumn(issueId: number) {
    return columns.find((c) => c.issues.some((i) => i.id === issueId));
  }

  function onDragStart(e: DragStartEvent) {
    const issue = allIssues.find((i) => i.id === e.active.id);
    setActiveIssue(issue || null);
  }

  async function onDragEnd(e: DragEndEvent) {
    setActiveIssue(null);
    const { active, over } = e;
    if (!over) return;
    const activeId = Number(active.id);
    const sourceCol = findColumn(activeId);
    if (!sourceCol) return;

    // `over` is either a card id or a column droppable id ("col-<statusId>")
    let destStatusId: number;
    let destCol: BoardColumn | undefined;
    if (typeof over.id === "string" && over.id.startsWith("col-")) {
      destStatusId = Number(over.id.slice(4));
      destCol = columns.find((c) => c.status.id === destStatusId);
    } else {
      destCol = findColumn(Number(over.id));
      destStatusId = destCol?.status.id ?? sourceCol.status.id;
    }
    if (!destCol) return;

    const overIndex = typeof over.id === "number"
      ? destCol.issues.findIndex((i) => i.id === Number(over.id))
      : destCol.issues.length;

    const activeIssue = sourceCol.issues.find((i) => i.id === activeId)!;
    if (sourceCol.status.id === destStatusId && overIndex === destCol.issues.findIndex((i) => i.id === activeId)) {
      return; // no move
    }

    // Optimistic reorder
    const next = columns.map((c) => ({ ...c, issues: [...c.issues] }));
    const src = next.find((c) => c.status.id === sourceCol.status.id)!;
    const dst = next.find((c) => c.status.id === destStatusId)!;
    src.issues = src.issues.filter((i) => i.id !== activeId);
    const insertAt = overIndex < 0 ? dst.issues.length : overIndex;
    const moved = { ...activeIssue, status: dst.status };
    dst.issues.splice(insertAt, 0, moved);
    setColumns(next);

    // Compute a fractional rank between neighbours
    const before = dst.issues[insertAt - 1]?.board_rank;
    const after = dst.issues[insertAt + 1]?.board_rank;
    let rank: number;
    if (before != null && after != null) rank = (before + after) / 2;
    else if (before != null) rank = before + 1;
    else if (after != null) rank = after - 1;
    else rank = 1;

    try {
      await api(`/issues/${activeIssue.key}/move`, {
        method: "POST",
        body: { status_id: destStatusId, rank },
      });
      qc.invalidateQueries({ queryKey: ["board", key] });
      qc.invalidateQueries({ queryKey: ["issue", activeIssue.key] });
    } catch {
      toast(`Couldn't move ${activeIssue.key}. Reverting.`, "error");
      if (board) setColumns(board.columns);
    }
  }

  if (isLoading && columns.length === 0) return <CenterSpinner />;

  return (
    <div className="flex h-full flex-col">
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2 border-b bg-surface px-4 py-2 text-sm">
        <button
          className={`badge ${filters.mine ? "bg-brand text-white" : "bg-surface-2 text-fg-subtle"}`}
          onClick={() => setFilters((f) => ({ ...f, mine: !f.mine }))}
        >My issues</button>
        <select className="input h-8 w-auto" value={(filters.assignee as number) || ""}
          onChange={(e) => setFilters((f) => ({ ...f, assignee: Number(e.target.value) || "" }))}>
          <option value="">All assignees</option>
          {members?.map((m) => <option key={m.user.id} value={m.user.id}>{m.user.name}</option>)}
        </select>
        <select className="input h-8 w-auto" value={(filters.priority as number) || ""}
          onChange={(e) => setFilters((f) => ({ ...f, priority: Number(e.target.value) || "" }))}>
          <option value="">All priorities</option>
          {meta?.priorities.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select className="input h-8 w-auto" value={(filters.type as number) || ""}
          onChange={(e) => setFilters((f) => ({ ...f, type: Number(e.target.value) || "" }))}>
          <option value="">All types</option>
          {meta?.types.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        {Object.values(filters).some(Boolean) && (
          <button className="text-xs text-muted hover:text-fg" onClick={() => setFilters({})}>Clear</button>
        )}
      </div>

      {/* Board */}
      <div className="min-h-0 flex-1 overflow-x-auto">
        <DndContext sensors={sensors} collisionDetection={closestCorners}
          onDragStart={onDragStart} onDragEnd={onDragEnd}>
          <div className="flex h-full gap-3 p-4">
            {columns.map((col) => (
              <Column key={col.status.id} col={col} writable={writable}
                onAdd={() => setCreateStatus(col.status.id)}
                onOpen={(k) => setOpenIssueKey(k)} />
            ))}
          </div>
          <DragOverlay>{activeIssue ? <div className="w-64"><IssueCard issue={activeIssue} /></div> : null}</DragOverlay>
        </DndContext>
      </div>

      <CreateIssueModal open={createStatus != null} onClose={() => setCreateStatus(null)}
        defaultProjectKey={key} defaultStatusId={createStatus || undefined}
        onCreated={() => { setCreateStatus(null); qc.invalidateQueries({ queryKey: ["board", key] }); }} />

      <Drawer open={!!openIssueKey} onClose={() => setOpenIssueKey(null)}>
        {openIssueKey && (
          <div>
            <div className="flex items-center justify-between border-b px-4 py-2">
              <a href={`/issues/${openIssueKey}`} className="text-xs text-muted hover:text-brand">Open full page ↗</a>
              <button className="btn-ghost h-7 px-2 text-xs" onClick={() => setOpenIssueKey(null)}>Close</button>
            </div>
            <IssueDetailView issueKey={openIssueKey} compact />
          </div>
        )}
      </Drawer>
    </div>
  );
}

function Column({ col, writable, onAdd, onOpen }: {
  col: BoardColumn; writable: boolean; onAdd: () => void; onOpen: (key: string) => void;
}) {
  const { setNodeRef } = useSortable({ id: `col-${col.status.id}`, data: { type: "column" } });
  return (
    <div className="flex w-72 shrink-0 flex-col rounded-lg bg-surface-2/60">
      <div className="flex items-center gap-2 px-3 py-2">
        <span className="h-2 w-2 rounded-full" style={{ background: col.status.color }} />
        <span className="text-sm font-medium">{col.status.name}</span>
        <span className="text-xs text-muted">{col.issues.length}</span>
        {writable && (
          <button onClick={onAdd} className="ml-auto text-muted hover:text-fg" aria-label={`Add issue to ${col.status.name}`}>
            <Plus size={15} />
          </button>
        )}
      </div>
      <div ref={setNodeRef} className="min-h-[60px] flex-1 space-y-2 overflow-y-auto px-2 pb-2">
        <SortableContext items={col.issues.map((i) => i.id)} strategy={verticalListSortingStrategy}>
          {col.issues.map((issue) => (
            <SortableCard key={issue.id} issue={issue} disabled={!writable} onOpen={onOpen} />
          ))}
        </SortableContext>
        {col.issues.length === 0 && (
          <div className="rounded-md border border-dashed py-6 text-center text-xs text-muted">No issues</div>
        )}
      </div>
    </div>
  );
}

function SortableCard({ issue, disabled, onOpen }: { issue: IssueSummary; disabled: boolean; onOpen: (key: string) => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: issue.id, disabled,
  });
  return (
    <div ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.4 : 1 }}
      {...attributes} {...listeners}>
      <IssueCard issue={issue} onOpen={onOpen} />
    </div>
  );
}
