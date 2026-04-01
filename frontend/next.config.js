/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const backend = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    return [
      {
        source: "/api/backend/:path*",
        destination: `${backend}/:path*`,
      },
      {
        source: "/files/:path*",
        destination: `${backend}/files/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
