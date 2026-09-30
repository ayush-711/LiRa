"use client";

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Plus, Check, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useLabels } from "@/lib/queries";
import { useToast } from "@/lib/toast";
import { cn } from "@/lib/utils";
import type { Label } from "@/lib/types";

// A restrained, professional Japandi-leaning palette for new labels.
export const LABEL_COLORS = [
  "#8a6f5c", "#6b7a5e", "#5f7a86", "#9c7b3f", "#a15c4e",
  "#6d6a8a", "#7a8a6f", "#8a6a72", "#5c7a72", "#8a8577",
];

export function LabelChipList({ value, labels }: { value: number[]; labels: Label[] }) {
  const selected = labels.filter((l) => value.includes(l.id));
  return (
    <div className="flex flex-wrap gap-1">
      {selected.map((l) => (
        <span key={l.id} className="badge"
          style={{ background: `${l.color}1f`, color: l.color, border: `1px solid ${l.color}40` }}>
          {l.name}
        </span>
      ))}
    </div>
  );
}

export function LabelPicker({
  value,
  onChange,
  canCreate = true,
}: {
  value: number[];
  onChange: (ids: number[]) => void;
  canCreate?: boolean;
}) {
  const { data: labels } = useLabels();
  const qc = useQueryClient();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [color, setColor] = useState(LABEL_COLORS[0]);
  const [creating, setCreating] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener("mousedown", onClick);
    return () => window.removeEventListener("mousedown", onClick);
  }, [open]);

  const all = labels || [];
  const selected = all.filter((l) => value.includes(l.id));
  const filtered = all.filter((l) => l.name.toLowerCase().includes(query.toLowerCase()));
  const exactExists = all.some((l) => l.name.toLowerCase() === query.trim().toLowerCase());

  function toggle(id: number) {
    onChange(value.includes(id) ? value.filter((i) => i !== id) : [...value, id]);
  }

  async function createLabel() {
    const name = query.trim();
    if (!name || creating) return;
    setCreating(true);
    try {
      const label = await api<Label>("/labels", { method: "POST", body: { name, color } });
      await qc.invalidateQueries({ queryKey: ["labels"] });
      onChange([...value, label.id]);
      setQuery("");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Couldn't create label", "error");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="relative" ref={ref}>
      <div className="flex flex-wrap items-center gap-1">
        {selected.map((l) => (
          <span key={l.id} className="badge group"
            style={{ background: `${l.color}1f`, color: l.color, border: `1px solid ${l.color}40` }}>
            {l.name}
            <button onClick={() => toggle(l.id)} className="opacity-60 hover:opacity-100" aria-label={`Remove ${l.name}`}>
              <X size={11} />
            </button>
          </span>
        ))}
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="badge border border-dashed border-border text-muted transition-colors hover:border-brand hover:text-brand"
        >
          <Plus size={12} /> Label
        </button>
      </div>

      {open && (
        <div className="absolute z-40 mt-1.5 w-60 rounded-xl border bg-surface p-2 shadow-pop">
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search or create…"
            className="input h-8 text-sm"
            onKeyDown={(e) => { if (e.key === "Enter" && !exactExists && canCreate) { e.preventDefault(); createLabel(); } }}
          />
          <div className="mt-1.5 max-h-44 overflow-y-auto">
            {filtered.map((l) => {
              const active = value.includes(l.id);
              return (
                <button key={l.id} onClick={() => toggle(l.id)}
                  className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-surface-2">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: l.color }} />
                  <span className="flex-1 truncate">{l.name}</span>
                  {active && <Check size={14} className="text-brand" />}
                </button>
              );
            })}
            {filtered.length === 0 && !query && (
              <p className="px-2 py-2 text-xs text-muted">No labels yet.</p>
            )}
          </div>

          {canCreate && query.trim() && !exactExists && (
            <div className="mt-1.5 border-t pt-2">
              <div className="mb-1.5 flex flex-wrap gap-1">
                {LABEL_COLORS.map((c) => (
                  <button key={c} onClick={() => setColor(c)}
                    className={cn("h-5 w-5 rounded-full ring-offset-1 ring-offset-surface transition", color === c && "ring-2 ring-brand")}
                    style={{ background: c }} aria-label={`Colour ${c}`} />
                ))}
              </div>
              <button onClick={createLabel} disabled={creating}
                className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-surface-2">
                <Plus size={13} className="text-brand" />
                Create <span className="font-medium" style={{ color }}>“{query.trim()}”</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
