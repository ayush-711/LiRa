// Typed API client. Talks to the same-origin /api (proxied by Next in dev,
// by Caddy in prod). Sends the CSRF token on mutations and normalises errors.

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "/api";

export class ApiError extends Error {
  code: string;
  status: number;
  details?: unknown;
  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : null;
}

type Options = {
  method?: string;
  body?: unknown;
  formData?: FormData;
  signal?: AbortSignal;
};

export async function api<T>(path: string, opts: Options = {}): Promise<T> {
  const method = opts.method || "GET";
  const headers: Record<string, string> = {};
  const isMutation = !["GET", "HEAD"].includes(method);

  if (isMutation) {
    const csrf = getCookie("lira_csrf");
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }

  let body: BodyInit | undefined;
  if (opts.formData) {
    body = opts.formData;
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body,
    credentials: "include",
    signal: opts.signal,
  });

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;

  if (!res.ok) {
    const err = data?.error || {};
    throw new ApiError(res.status, err.code || "ERROR", err.message || res.statusText, err.details);
  }
  return data as T;
}

export const apiBase = BASE;
