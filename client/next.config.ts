import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  // Optimize image handling for production
  images: {
    unoptimized: false,
    formats: ["image/webp", "image/avif"],
  },

  // Production environment variables
  env: {
    NEXT_PUBLIC_FASTAPI_WS_URL: process.env.NEXT_PUBLIC_FASTAPI_WS_URL,
    NEXT_PUBLIC_FASTAPI_HTTP_URL: process.env.NEXT_PUBLIC_FASTAPI_HTTP_URL,
  },

  // Optimize for production builds
  productionBrowserSourceMaps: false,
  compress: true,
  poweredByHeader: false,

  // React strict mode for detecting potential issues
  reactStrictMode: true,
};

export default nextConfig;
