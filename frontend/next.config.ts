import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
  	  root: __dirname,
  },
  allowedDevOrigins: ['usebreadcrumbs.app', 'localhost:3000'],
};

export default nextConfig;
