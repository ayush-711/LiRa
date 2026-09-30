"use client";

import { Menu, MenuItem } from "@/components/ui/misc";

export function InlineSelect<T extends { id: number }>({
  label,
  value,
  options,
  render,
  onChange,
  disabled,
}: {
  label: string;
  value: T | null | undefined;
  options: T[];
  render: (o: T | null) => React.ReactNode;
  onChange: (id: number | null) => void;
  disabled?: boolean;
}) {
  if (disabled) {
    return <div className="flex items-center gap-1.5 px-1.5 py-1 text-sm">{render(value ?? null)}</div>;
  }
  return (
    <Menu
      align="left"
      trigger={
        <span className="flex items-center gap-1.5 rounded px-1.5 py-1 text-sm hover:bg-surface-2" aria-label={label}>
          {render(value ?? null)}
        </span>
      }
    >
      {(close) => (
        <div className="max-h-64 overflow-y-auto">
          <MenuItem onClick={() => { onChange(null); close(); }}>{render(null)}</MenuItem>
          {options.map((o) => (
            <MenuItem key={o.id} onClick={() => { onChange(o.id); close(); }}>
              {render(o)}
            </MenuItem>
          ))}
        </div>
      )}
    </Menu>
  );
}
