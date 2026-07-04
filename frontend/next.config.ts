import type { NextConfig } from "next";

const useStandaloneOutput = process.env.NEXT_OUTPUT_STANDALONE === "true";

const nextConfig: NextConfig = {
  ...(useStandaloneOutput ? { output: "standalone" as const } : {}),
  experimental: {
    cpus: 1,
    workerThreads: false,
  },
};

export default nextConfig;
