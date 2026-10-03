import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // A static site: every page is built from the saved run files in ../runs (no server, no API). Host the `out`
  // folder anywhere.
  output: "export",
  trailingSlash: true,
};

export default nextConfig;
