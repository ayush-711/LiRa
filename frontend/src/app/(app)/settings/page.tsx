"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useNotificationPrefs } from "@/lib/queries";
import { useToast } from "@/lib/toast";
import { useTheme, type ThemeMode } from "@/lib/theme";
import { Sun, Moon, Monitor } from "lucide-react";
import { cn } from "@/lib/utils";
import { useQueryClient } from "@tanstack/react-query";
import { Avatar } from "@/components/ui/Avatar";
import type { NotificationPreferences } from "@/lib/types";

const PREF_LABELS: Record<keyof NotificationPreferences, string> = {
  email_on_assignment: "When I'm assigned an issue",
  email_on_mention: "When I'm mentioned",
  email_on_comment: "New comments on my issues",
  email_on_due_reminder: "Due-date reminders",
  email_on_status_change: "Status changes on my issues",
};

export default function SettingsPage() {
  const { user, refresh, logout } = useAuth();
  const { data: prefs } = useNotificationPrefs();
  const { mode, setMode } = useTheme();
  const qc = useQueryClient();
  const toast = useToast();

  const [name, setName] = useState(user?.name || "");
  const [cur, setCur] = useState("");
  const [next, setNext] = useState("");

  useEffect(() => { if (user) setName(user.name); }, [user]);

  async function saveProfile() {
    try {
      await api("/account/profile", { method: "PATCH", body: { name } });
      await refresh();
      toast("Profile updated");
    } catch (err) { toast(err instanceof ApiError ? err.message : "Failed", "error"); }
  }
  async function changePassword() {
    try {
      await api("/account/password", { method: "POST", body: { current_password: cur, new_password: next } });
      setCur(""); setNext("");
      toast("Password changed");
    } catch (err) { toast(err instanceof ApiError ? err.message : "Failed", "error"); }
  }
  async function togglePref(k: keyof NotificationPreferences, v: boolean) {
    await api("/account/notification-preferences", { method: "PATCH", body: { [k]: v } });
    qc.invalidateQueries({ queryKey: ["notif-prefs"] });
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-5">
      <h1 className="text-lg font-semibold">Settings</h1>

      <section className="card p-4">
        <h2 className="mb-1 text-sm font-semibold">Appearance</h2>
        <p className="mb-3 text-sm text-muted">Choose how LiRa looks to you.</p>
        <div className="grid max-w-md grid-cols-3 gap-2">
          {([
            { m: "light" as ThemeMode, label: "Light", icon: Sun },
            { m: "dark" as ThemeMode, label: "Dark", icon: Moon },
            { m: "system" as ThemeMode, label: "System", icon: Monitor },
          ]).map(({ m, label, icon: Icon }) => (
            <button key={m} onClick={() => setMode(m)}
              className={cn(
                "flex flex-col items-center gap-1.5 rounded-lg border px-3 py-3 text-sm transition-colors",
                mode === m ? "border-brand bg-brand-soft text-brand" : "hover:bg-surface-2"
              )}>
              <Icon size={18} />
              {label}
            </button>
          ))}
        </div>
      </section>

      <section className="card p-4">
        <h2 className="mb-3 text-sm font-semibold">Profile</h2>
        <div className="flex items-center gap-3">
          <Avatar user={user} size={44} />
          <div className="flex-1">
            <label className="label-text">Display name</label>
            <input className="input mt-1" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
        </div>
        <p className="mt-2 text-xs text-muted">Email: {user?.email} (managed by your administrator)</p>
        <button className="btn-primary mt-3" onClick={saveProfile}>Save profile</button>
      </section>

      <section className="card p-4">
        <h2 className="mb-3 text-sm font-semibold">Change password</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="label-text">Current password</label>
            <input type="password" className="input mt-1" value={cur} onChange={(e) => setCur(e.target.value)} />
          </div>
          <div>
            <label className="label-text">New password</label>
            <input type="password" className="input mt-1" value={next} onChange={(e) => setNext(e.target.value)} />
          </div>
        </div>
        <button className="btn-primary mt-3" onClick={changePassword} disabled={!cur || next.length < 8}>Update password</button>
      </section>

      <section className="card p-4">
        <h2 className="mb-3 text-sm font-semibold">Email notifications</h2>
        <div className="space-y-2">
          {prefs && (Object.keys(PREF_LABELS) as (keyof NotificationPreferences)[]).map((k) => (
            <label key={k} className="flex items-center justify-between text-sm">
              <span className="text-fg-subtle">{PREF_LABELS[k]}</span>
              <input type="checkbox" checked={prefs[k]} onChange={(e) => togglePref(k, e.target.checked)} className="h-4 w-4" />
            </label>
          ))}
        </div>
      </section>

      <section className="card p-4">
        <button className="btn-outline text-red-600" onClick={logout}>Sign out</button>
      </section>
    </div>
  );
}
