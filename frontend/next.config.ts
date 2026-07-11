import type { NextConfig } from "next";

const useStandaloneOutput = process.env.NEXT_OUTPUT_STANDALONE === "true";
const distDir = process.env.NODE_ENV === "production" ? ".next-production" : ".next";

const nextConfig: NextConfig = {
  distDir,
  ...(useStandaloneOutput ? { output: "standalone" as const } : {}),
  experimental: {
    cpus: 1,
    workerThreads: false,
  },
};

export default nextConfig;
