/** @type {import('next').NextConfig} */
const isDev = process.env.NODE_ENV === 'development';

const nextConfig = {
  images: {
    unoptimized: true,
  },
  // In dev, proxy /api/* to the FastAPI backend so the SPA can talk to it
  // without CORS. In a production build we emit a static export for FastAPI to
  // serve on the same origin. The two are mutually exclusive (rewrites are
  // unsupported with `output: export`), so we pick one based on the mode.
  ...(isDev
    ? {
        async rewrites() {
          return [
            {
              // Use 127.0.0.1 (not "localhost") so the proxy doesn't try IPv6
              // ::1 first — uvicorn binds IPv4 by default and refuses ::1,
              // which otherwise breaks the SSE stream and crashes `next dev`.
              source: '/api/:path*',
              destination: 'http://127.0.0.1:8000/api/:path*',
            },
          ];
        },
      }
    : {
        output: 'export',
      }),
};

module.exports = nextConfig;
