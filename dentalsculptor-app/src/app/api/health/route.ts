import { NextResponse } from "next/server";
import { clerkKeyDiagnostics } from "@/lib/clerk-proxy";

/** Lightweight deploy diagnostics — safe to expose (no secrets). */
export async function GET() {
  const clerk = clerkKeyDiagnostics();

  return NextResponse.json({
    ok: true,
    timestamp: new Date().toISOString(),
    clerk,
    app: {
      url: process.env.NEXT_PUBLIC_APP_URL ?? null,
      vercelHost: process.env.VERCEL_PROJECT_PRODUCTION_URL ?? process.env.VERCEL_URL ?? null,
      previewMode: process.env.UI_PREVIEW_MODE === "true",
    },
    database: {
      configured: Boolean(process.env.DATABASE_URL),
      pooler: process.env.DATABASE_URL?.includes(":6543") ?? false,
    },
    modal: {
      asyncS3: process.env.MODAL_ASYNC_S3_ENABLED === "true",
      hasGenerateUrl: Boolean(process.env.MODAL_GENERATE_ASYNC_URL),
    },
    hints: [
      !clerk.keyPairMatch
        ? "CLERK_SECRET_KEY and NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY must be from the same Clerk app (both test or both live)."
        : null,
      clerk.keyType === "development" && !clerk.proxyUrl
        ? "Dev keys on Vercel need NEXT_PUBLIC_CLERK_PROXY_URL or a *.vercel.app host."
        : null,
    ].filter(Boolean),
  });
}
