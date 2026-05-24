import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_FASTAPI_WS_URL: process.env.NEXT_PUBLIC_FASTAPI_WS_URL,
    NEXT_PUBLIC_FASTAPI_HTTP_URL: process.env.NEXT_PUBLIC_FASTAPI_HTTP_URL,
  },
};

export default nextConfig;
