"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard, CircleUser, FolderKanban, Users, Bell,
  Settings, Search, Plus, LogOut, ScrollText, History, Menu as MenuIcon,
  ArrowLeft, ArrowRight,
  X, Keyboard, Sun, Moon,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useUnreadCount } from "@/lib/queries";
import { useRealtime } from "@/lib/realtime";
import { useTheme } from "@/lib/theme";
import { cn, ROLE_LABELS } from "@/lib/utils";
import { Avatar } from "@/components/ui/Avatar";
import { Menu, MenuItem } from "@/components/ui/misc";
import { CommandPalette } from "@/components/CommandPalette";
import { CreateIssueModal } from "@/components/CreateIssueModal";
import { ShortcutsModal } from "@/components/ShortcutsModal";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/my-issues", label: "My Issues", icon: CircleUser },
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/activity", label: "Activity", icon: History },
  { href: "/team", label: "Team", icon: Users },
  { href: "/notifications", label: "Notifications", icon: Bell },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const { data: unread } = useUnreadCount();
  const { resolved, setMode } = useTheme();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const gPressed = useRef(false);

  // Live updates (additive — the app works fine if the socket can't connect).
  useRealtime(!!user);

  // Close the mobile drawer whenever the route changes.
  useEffect(() => setNavOpen(false), [pathname]);

  useEffect(() => {
    const isTyping = () => {
      const el = document.activeElement;
      return el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || (el as HTMLElement).isContentEditable);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.altKey && e.key === "ArrowLeft") { e.preventDefault(); router.back(); return; }
      if (e.altKey && e.key === "ArrowRight") { e.preventDefault(); router.forward(); return; }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((o) => !o);
        return;
      }
      if (isTyping() || e.metaKey || e.ctrlKey || e.altKey) return;
      if (gPressed.current) {
        gPressed.current = false;
        const map: Record<string, string> = { d: "/dashboard", m: "/my-issues", p: "/projects", t: "/team" };
        if (map[e.key.toLowerCase()]) { e.preventDefault(); router.push(map[e.key.toLowerCase()]); }
        return;
      }
      if (e.key === "g") { gPressed.current = true; setTimeout(() => (gPressed.current = false), 800); return; }
      if (e.key === "?") { e.preventDefault(); setShortcutsOpen(true); return; }
      if (e.key === "c") { e.preventDefault(); setCreateOpen(true); }
      if (e.key === "/") { e.preventDefault(); setPaletteOpen(true); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [router]);

  const canCreate = user && user.role !== "viewer";

  const navContent = (
    <>
      <div className="flex h-16 items-center gap-2.5 px-4">
        <Link href="/dashboard" className="flex items-center gap-2.5 rounded-lg transition-opacity hover:opacity-80">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand text-lg font-bold text-brand-fg">L</span>
          <span className="text-lg font-semibold tracking-tight">LiRa</span>
        </Link>
        <button
          className="ml-auto text-muted hover:text-fg md:hidden"
          onClick={() => setNavOpen(false)}
          aria-label="Close navigation"
        >
          <X size={18} />
        </button>
      </div>
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-2">
        {NAV.map(({ href, label, icon: Icon }) => {
          const activeItem = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link key={href} href={href}
              className={cn(
                "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors",
                activeItem ? "bg-brand-soft font-medium text-brand" : "text-fg-subtle hover:bg-surface-2"
              )}>
              <Icon size={16} />
              <span>{label}</span>
              {href === "/notifications" && unread && unread.count > 0 ? (
                <span className="ml-auto rounded-full bg-brand px-1.5 text-[10px] font-medium text-brand-fg">
                  {unread.count}
                </span>
              ) : null}
            </Link>
          );
        })}
        {user?.role === "admin" && (
          <>
            <div className="px-2.5 pb-1 pt-4 text-[11px] font-semibold uppercase tracking-wide text-muted">Admin</div>
            <Link href="/admin/audit" className={cn("flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors",
              pathname.startsWith("/admin/audit") ? "bg-brand-soft font-medium text-brand" : "text-fg-subtle hover:bg-surface-2")}>
              <ScrollText size={16} /> Audit Log
            </Link>
          </>
        )}
      </nav>
      <div className="border-t p-2">
        <button onClick={() => setShortcutsOpen(true)}
          className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm text-muted hover:bg-surface-2">
          <Keyboard size={16} /> Shortcuts
        </button>
      </div>
    </>
  );

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Desktop sidebar */}
      <aside className="hidden w-56 shrink-0 flex-col border-r bg-surface md:flex">{navContent}</aside>

      {/* Mobile drawer */}
      {navOpen && (
        <div className="fixed inset-0 z-50 md:hidden" onMouseDown={() => setNavOpen(false)}>
          <div className="absolute inset-0 bg-black/40" />
          <aside
            className="absolute left-0 top-0 flex h-full w-64 flex-col border-r bg-surface shadow-pop"
            onMouseDown={(e) => e.stopPropagation()}
          >
            {navContent}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-2 border-b bg-surface px-3 sm:px-4">
          <button
            className="btn-ghost h-9 w-9 shrink-0 p-0 md:hidden"
            onClick={() => setNavOpen(true)}
            aria-label="Open navigation"
          >
            <MenuIcon size={18} />
          </button>

          {/* In-app history nav so the browser chrome isn't the only way back. */}
          <div className="hidden shrink-0 items-center gap-0.5 sm:flex">
            <button
              onClick={() => router.back()}
              className="btn-ghost h-9 w-8 p-0"
              aria-label="Go back"
              title="Back (Alt+←)"
            >
              <ArrowLeft size={17} />
            </button>
            <button
              onClick={() => router.forward()}
              className="btn-ghost h-9 w-8 p-0"
              aria-label="Go forward"
              title="Forward (Alt+→)"
            >
              <ArrowRight size={17} />
            </button>
          </div>

          <button onClick={() => setPaletteOpen(true)}
            className="flex h-9 max-w-md flex-1 items-center gap-2 rounded-lg border bg-bg px-3 text-sm text-muted transition-colors hover:bg-surface-2">
            <Search size={15} />
            <span className="hidden sm:inline">Search…</span>
          </button>

          <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
            {canCreate && (
              <button
                onClick={() => setCreateOpen(true)}
                className="btn-primary h-9 gap-2 px-3 font-semibold shadow-soft sm:px-4"
              >
                <Plus size={17} strokeWidth={2.6} />
                <span className="hidden sm:inline">New issue</span>
              </button>
            )}
            <button
              onClick={() => setMode(resolved === "dark" ? "light" : "dark")}
              className="btn-ghost h-9 w-9 p-0"
              aria-label={resolved === "dark" ? "Switch to light theme" : "Switch to dark theme"}
              title={resolved === "dark" ? "Light mode" : "Dark mode"}
            >
              {resolved === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <Link href="/notifications" className="btn-ghost relative h-9 w-9 p-0" aria-label="Notifications">
              <Bell size={18} />
              {unread && unread.count > 0 && (
                <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-red-500" />
              )}
            </Link>
            <Menu trigger={<span className="flex items-center"><Avatar user={user} size={30} /></span>}>
              {(close) => (
                <>
                  <div className="border-b px-2 py-2">
                    <p className="text-sm font-medium">{user?.name}</p>
                    <p className="text-xs text-muted">{user && ROLE_LABELS[user.role]}</p>
                  </div>
                  <MenuItem onClick={() => { close(); router.push("/settings"); }}>
                    <Settings size={14} /> Settings
                  </MenuItem>
                  <MenuItem onClick={() => { close(); setShortcutsOpen(true); }}>
                    <Keyboard size={14} /> Shortcuts
                  </MenuItem>
                  <MenuItem danger onClick={() => { close(); logout(); }}>
                    <LogOut size={14} /> Sign out
                  </MenuItem>
                </>
              )}
            </Menu>
          </div>
        </header>

        <main className="min-h-0 flex-1 overflow-y-auto">{children}</main>
      </div>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} onCreateIssue={() => setCreateOpen(true)} />
      <CreateIssueModal open={createOpen} onClose={() => setCreateOpen(false)} />
      <ShortcutsModal open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
    </div>
  );
}
