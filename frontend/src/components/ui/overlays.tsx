"use client";

import { useEffect } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

function useEsc(onClose: () => void) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
}

export function Modal({
  open,
  onClose,
  title,
  children,
  wide,
}: {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  wide?: boolean;
}) {
  useEsc(onClose);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/30 p-4 pt-[8vh]" onMouseDown={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={cn("card w-full shadow-pop", wide ? "max-w-2xl" : "max-w-md")}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {title && (
          <div className="flex items-center justify-between border-b px-4 py-3">
            <h2 className="text-sm font-semibold">{title}</h2>
            <button onClick={onClose} className="text-muted hover:text-fg" aria-label="Close">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}

export function Drawer({
  open,
  onClose,
  children,
  width = 640,
}: {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  width?: number;
}) {
  useEsc(onClose);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30" onMouseDown={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        className="h-full overflow-y-auto bg-surface shadow-pop"
        style={{ width: `min(${width}px, 100%)` }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}
