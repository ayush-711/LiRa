"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Spinner } from "@/components/ui/misc";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await api("/auth/forgot-password", { method: "POST", body: { email } });
    } finally {
      setSent(true);
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-4 text-center text-lg font-semibold">Reset your password</h1>
        {sent ? (
          <div className="card p-5 text-center text-sm">
            If an account exists for that email, a reset link has been sent.
            <div className="mt-3">
              <Link href="/login" className="text-brand hover:underline">Back to sign in</Link>
            </div>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="card space-y-3 p-5">
            <div>
              <label className="label-text">Email</label>
              <input required type="email" autoFocus className="input mt-1" value={email}
                onChange={(e) => setEmail(e.target.value)} />
            </div>
            <button className="btn-primary w-full" disabled={loading}>
              {loading ? <Spinner className="text-white" /> : "Send reset link"}
            </button>
            <div className="text-center">
              <Link href="/login" className="text-xs text-muted hover:text-fg">Back to sign in</Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
