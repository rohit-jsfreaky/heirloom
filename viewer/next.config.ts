import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Run data only changes when the pipeline is re-run, so pages are cached and prerendered (`'use cache'`).
  cacheComponents: true,
};

export default nextConfig;
