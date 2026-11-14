import type { NextConfig } from "next";

// Every page reads the login cookie and fresh data from the Python API, so pages render per request.
// Cache Components stays off: nothing here is safe to cache across users.
const nextConfig: NextConfig = {
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
