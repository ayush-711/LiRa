"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Spinner } from "@/components/ui/misc";

export default function LoginPage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api("/auth/login", { method: "POST", body: { email, password } });
      await refresh();
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-brand text-lg font-bold text-white">
            L
          </div>
          <h1 className="text-lg font-semibold">Sign in to LiRa</h1>
          <p className="text-sm text-muted">Internal work management</p>
        </div>
        <form onSubmit={onSubmit} className="card space-y-3 p-5">
          {error && (
            <div className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400" role="alert">
              {error}
            </div>
          )}
          <div>
            <label className="label-text" htmlFor="email">Email</label>
            <input id="email" type="email" required autoFocus className="input mt-1"
              value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <label className="label-text" htmlFor="password">Password</label>
            <input id="password" type="password" required className="input mt-1"
              value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? <Spinner className="text-white" /> : "Sign in"}
          </button>
          <div className="text-center">
            <Link href="/forgot-password" className="text-xs text-muted hover:text-fg">
              Forgot your password?
            </Link>
          </div>
        </form>
        <p className="mt-4 text-center text-xs text-muted">
          Access is invitation-only. Contact an administrator for an invite.
        </p>
      </div>
    </div>
  );
}
