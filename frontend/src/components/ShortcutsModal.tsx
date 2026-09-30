"use client";

import { Modal } from "@/components/ui/overlays";

const GROUPS: { title: string; items: [string, string][] }[] = [
  {
    title: "General",
    items: [
      ["⌘K / Ctrl K", "Open command palette"],
      ["/", "Search"],
      ["C", "Create issue"],
      ["?", "Show this help"],
      ["Esc", "Close dialog"],
    ],
  },
  {
    title: "Navigation",
    items: [
      ["G then D", "Dashboard"],
      ["G then M", "My Issues"],
      ["G then P", "Projects"],
      ["G then T", "Team"],
      ["Alt ←", "Back"],
      ["Alt →", "Forward"],
    ],
  },
  {
    title: "Writing",
    items: [
      ["@", "Mention a teammate"],
      ["⌘↵ / Ctrl ↵", "Send comment"],
    ],
  },
];

export function ShortcutsModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Modal open={open} onClose={onClose} title="Keyboard shortcuts" wide>
      <div className="grid gap-6 sm:grid-cols-2">
        {GROUPS.map((g) => (
          <div key={g.title}>
            <h3 className="label-text mb-2">{g.title}</h3>
            <div className="space-y-1.5">
              {g.items.map(([keys, label]) => (
                <div key={keys} className="flex items-center justify-between gap-4 text-sm">
                  <span className="text-fg-subtle">{label}</span>
                  <kbd className="shrink-0 rounded border bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-fg-subtle">
                    {keys}
                  </kbd>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Modal>
  );
}
