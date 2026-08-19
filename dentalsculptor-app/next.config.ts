import type { NextConfig } from "next";
import { resolveClerkProxyUrl } from "./src/lib/clerk-proxy";

function supabaseStorageHostname(): string | undefined {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  if (!url) return undefined;
  try {
    return new URL(url).hostname;
  } catch {
    return undefined;
  }
}

const supabaseHost = supabaseStorageHostname();
const clerkProxyUrl = resolveClerkProxyUrl();

const nextConfig: NextConfig = {
  ...(clerkProxyUrl
    ? { env: { NEXT_PUBLIC_CLERK_PROXY_URL: clerkProxyUrl } }
    : {}),
  images: {
    remotePatterns: [
      ...(supabaseHost
        ? [
            {
              protocol: "https" as const,
              hostname: supabaseHost,
              pathname: "/storage/v1/object/public/**",
            },
          ]
        : []),
      {
        protocol: "https",
        hostname: "v3b.fal.media",
        pathname: "/**",
      },
    ],
  },
};

export default nextConfig;
