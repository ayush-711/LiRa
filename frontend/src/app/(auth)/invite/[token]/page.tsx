"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Spinner } from "@/components/ui/misc";
import { ROLE_LABELS } from "@/lib/utils";

export default function InvitePage() {
  const { token } = useParams<{ token: string }>();
  const router = useRouter();
  const { refresh } = useAuth();
  const [info, setInfo] = useState<{ email: string; role: string } | null>(null);
  const [invalid, setInvalid] = useState(false);
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api<{ email: string; role: string }>(`/invitations/${token}`)
      .then(setInfo)
      .catch(() => setInvalid(true));
  }, [token]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api(`/invitations/${token}/accept`, { method: "POST", body: { name, password } });
      await refresh();
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  if (invalid)
    return (
      <Centered>
        <div className="card p-6 text-center">
          <h1 className="text-base font-semibold">Invitation invalid</h1>
          <p className="mt-1 text-sm text-muted">This invitation is invalid or has expired.</p>
        </div>
      </Centered>
    );

  if (!info)
    return (
      <Centered>
        <Spinner className="h-6 w-6" />
      </Centered>
    );

  return (
    <Centered>
      <div className="w-full max-w-sm">
        <h1 className="mb-1 text-center text-lg font-semibold">Join LiRa</h1>
        <p className="mb-4 text-center text-sm text-muted">
          {info.email} · {ROLE_LABELS[info.role] || info.role}
        </p>
        <form onSubmit={onSubmit} className="card space-y-3 p-5">
          {error && <div className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400">{error}</div>}
          <div>
            <label className="label-text">Your name</label>
            <input required autoFocus className="input mt-1" value={name}
              onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label className="label-text">Password</label>
            <input required type="password" minLength={8} className="input mt-1" value={password}
              onChange={(e) => setPassword(e.target.value)} />
            <p className="mt-1 text-xs text-muted">At least 8 characters, with letters and numbers.</p>
          </div>
          <button className="btn-primary w-full" disabled={loading}>
            {loading ? <Spinner className="text-white" /> : "Create account"}
          </button>
        </form>
      </div>
    </Centered>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return <div className="flex min-h-screen items-center justify-center bg-bg px-4">{children}</div>;
}
