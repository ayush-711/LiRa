"use client";

import { useMemo, useRef, useState } from "react";
import { Avatar } from "@/components/ui/Avatar";
import { cn } from "@/lib/utils";
import type { User } from "@/lib/types";

/** The handle the backend resolves mentions against (email local-part). */
export function handleFor(user: User): string {
  return user.email.split("@")[0].toLowerCase();
}

/**
 * Textarea with @mention autocomplete.
 *
 * Inserts the exact handle the server matches on, so a mention typed here always
 * resolves to a real notification — previously users had to guess the format.
 */
export function MentionTextarea({
  value,
  onChange,
  people,
  placeholder,
  className,
  onSubmit,
}: {
  value: string;
  onChange: (v: string) => void;
  people: User[];
  placeholder?: string;
  className?: string;
  onSubmit?: () => void;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const [caret, setCaret] = useState(0);
  const [active, setActive] = useState(0);
  const [dismissed, setDismissed] = useState(false);

  // The @token immediately before the caret, if any.
  const token = useMemo(() => {
    const upto = value.slice(0, caret);
    const match = /(^|\s)@([A-Za-z0-9._-]*)$/.exec(upto);
    if (!match) return null;
    return { query: match[2].toLowerCase(), start: caret - match[2].length - 1 };
  }, [value, caret]);

  const matches = useMemo(() => {
    if (!token || dismissed) return [];
    return people
      .filter((p) => {
        const h = handleFor(p);
        return h.startsWith(token.query) || p.name.toLowerCase().includes(token.query);
      })
      .slice(0, 6);
  }, [token, people, dismissed]);

  const open = matches.length > 0;

  function insert(user: User) {
    if (!token) return;
    const before = value.slice(0, token.start);
    const after = value.slice(caret);
    const next = `${before}@${handleFor(user)} ${after}`;
    onChange(next);
    setDismissed(true);
    requestAnimationFrame(() => {
      const pos = before.length + handleFor(user).length + 2;
      ref.current?.focus();
      ref.current?.setSelectionRange(pos, pos);
      setCaret(pos);
    });
  }

  function sync(e: React.SyntheticEvent<HTMLTextAreaElement>) {
    setCaret(e.currentTarget.selectionStart ?? 0);
  }

  return (
    <div className="relative">
      <textarea
        ref={ref}
        value={value}
        placeholder={placeholder}
        className={cn("input py-2", className)}
        onChange={(e) => {
          onChange(e.target.value);
          setCaret(e.target.selectionStart ?? 0);
          setDismissed(false);
          setActive(0);
        }}
        onClick={sync}
        onKeyUp={sync}
        onKeyDown={(e) => {
          if (open) {
            if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, matches.length - 1)); return; }
            if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); return; }
            if (e.key === "Enter" || e.key === "Tab") { e.preventDefault(); insert(matches[active]); return; }
            if (e.key === "Escape") { setDismissed(true); return; }
          }
          if (onSubmit && e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            onSubmit();
          }
        }}
      />
      {open && (
        <div className="absolute bottom-full z-40 mb-1 w-64 rounded-xl border bg-surface p-1 shadow-pop">
          {matches.map((p, i) => (
            <button
              key={p.id}
              type="button"
              onMouseEnter={() => setActive(i)}
              onMouseDown={(e) => { e.preventDefault(); insert(p); }}
              className={cn(
                "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm",
                i === active ? "bg-brand-soft text-brand" : "hover:bg-surface-2"
              )}
            >
              <Avatar user={p} size={20} />
              <span className="truncate">{p.name}</span>
              <span className="ml-auto shrink-0 font-mono text-xs text-muted">@{handleFor(p)}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
