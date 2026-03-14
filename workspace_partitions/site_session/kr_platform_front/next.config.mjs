/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,

  async rewrites() {
    // Proxy /_calc/* requests to the Python backend engine servers.
    // Vercel does not host the AI engines — they run on a separate server.
    // ENGINE_ORIGIN env var (server-side only) points to the backend.
    const engineOrigin =
      process.env.ENGINE_ORIGIN ||
      process.env.NEXT_PUBLIC_PRIVATE_ENGINE_ORIGIN ||
      "https://calc.seoulmna.co.kr";

    return [
      {
        source: "/_calc/:path*",
        destination: `${engineOrigin}/:path*`,
      },
    ];
  },

  async headers() {
    return [
      {
        // Security headers for all pages EXCEPT proxied engine paths.
        // /_calc/* is proxied to the backend which supplies its own headers.
        source: "/((?!_calc/).*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
          {
            key: "Strict-Transport-Security",
            value: "max-age=31536000; includeSubDomains",
          },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' https://va.vercel-scripts.com https://js.tosspayments.com",
              "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com",
              "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com",
              "img-src 'self' data: https:",
              "frame-src 'self' https://seoulmna.kr https://*.seoulmna.co.kr https://tosspayments.com https://*.tosspayments.com",
              "connect-src 'self' https://seoulmna.kr https://*.seoulmna.co.kr https://vitals.vercel-insights.com https://api.tosspayments.com https://js.tosspayments.com",
              "media-src 'self'",
              "worker-src 'self'",
              "manifest-src 'self'",
              "object-src 'none'",
              "base-uri 'self'",
              "form-action 'self'",
              "frame-ancestors 'self'",
            ].join("; "),
          },
          {
            key: "Cross-Origin-Opener-Policy",
            value: "same-origin-allow-popups",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
