"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "./api";
import type { User } from "./types";

interface AuthState {
  user: User | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  async function refresh() {
    try {
      const me = await api<User>("/auth/me");
      setUser(me);
    } catch (e) {
      if (e instanceof ApiError && (e.status === 401 || e.status === 403)) setUser(null);
    } finally {
      setLoading(false);
    }
  }

  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {
      /* ignore */
    }
    setUser(null);
    router.push("/login");
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, refresh, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function canWrite(user: User | null): boolean {
  return !!user && user.role !== "viewer";
}
