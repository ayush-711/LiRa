/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  // Types are checked via `npm run typecheck` / CI; don't block builds on lint.
  eslint: { ignoreDuringBuilds: true },
  async rewrites() {
    // In development, proxy /api to the backend so cookies stay same-origin.
    const backend = process.env.BACKEND_INTERNAL_URL || "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
