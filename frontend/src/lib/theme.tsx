"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

export type ThemeMode = "light" | "dark" | "system";

const STORAGE_KEY = "lira-theme";

interface ThemeCtx {
  mode: ThemeMode;
  resolved: "light" | "dark";
  setMode: (m: ThemeMode) => void;
}

const Ctx = createContext<ThemeCtx | null>(null);

function systemPrefersDark() {
  return typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function apply(mode: ThemeMode) {
  const resolved = mode === "system" ? (systemPrefersDark() ? "dark" : "light") : mode;
  document.documentElement.dataset.theme = resolved;
  document.documentElement.style.colorScheme = resolved;
  return resolved;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>("system");
  const [resolved, setResolved] = useState<"light" | "dark">("light");

  useEffect(() => {
    const stored = (localStorage.getItem(STORAGE_KEY) as ThemeMode) || "system";
    setModeState(stored);
    setResolved(apply(stored));

    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      const cur = (localStorage.getItem(STORAGE_KEY) as ThemeMode) || "system";
      if (cur === "system") setResolved(apply("system"));
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const setMode = useCallback((m: ThemeMode) => {
    localStorage.setItem(STORAGE_KEY, m);
    setModeState(m);
    setResolved(apply(m));
  }, []);

  return <Ctx.Provider value={{ mode, resolved, setMode }}>{children}</Ctx.Provider>;
}

export function useTheme() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}

// Inline script injected before hydration to prevent a flash of the wrong theme.
export const themeInitScript = `(function(){try{var m=localStorage.getItem("${STORAGE_KEY}")||"system";var d=m==="dark"||(m==="system"&&window.matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.dataset.theme=d?"dark":"light";document.documentElement.style.colorScheme=d?"dark":"light";}catch(e){}})();`;
