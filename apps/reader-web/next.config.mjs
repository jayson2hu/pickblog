/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  async redirects() {
    return [{ source: "/", destination: "/zh", permanent: false }];
  },
  async rewrites() {
    const target = process.env.READER_API_PROXY_TARGET;
    if (!target) return [];
    return [{ source: "/api/:path*", destination: `${target.replace(/\/$/, "")}/api/:path*` }];
  }
};

export default nextConfig;
