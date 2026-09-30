"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { Spinner } from "@/components/ui/misc";

export default function ResetPasswordPage() {
  const { token } = useParams<{ token: string }>();
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api("/auth/reset-password", { method: "POST", body: { token, new_password: password } });
      setDone(true);
      setTimeout(() => router.push("/login"), 1500);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-4 text-center text-lg font-semibold">Choose a new password</h1>
        {done ? (
          <div className="card p-5 text-center text-sm">
            Password updated. Redirecting to sign in…
            <div className="mt-3"><Link href="/login" className="text-brand hover:underline">Sign in</Link></div>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="card space-y-3 p-5">
            {error && <div className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400">{error}</div>}
            <div>
              <label className="label-text">New password</label>
              <input required type="password" minLength={8} autoFocus className="input mt-1"
                value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
            <button className="btn-primary w-full" disabled={loading}>
              {loading ? <Spinner className="text-white" /> : "Update password"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
