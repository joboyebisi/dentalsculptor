import { NextResponse } from "next/server";

/** Lightweight deploy diagnostics — safe to expose (no secrets). */
export async function GET() {
  const pk = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "";
  return NextResponse.json({
    ok: true,
    timestamp: new Date().toISOString(),
    clerk: {
      hasPublishableKey: pk.startsWith("pk_"),
      keyType: pk.startsWith("pk_live_") ? "production" : pk.startsWith("pk_test_") ? "development" : "missing",
      proxyUrl: process.env.NEXT_PUBLIC_CLERK_PROXY_URL ?? null,
      signInUrl: process.env.NEXT_PUBLIC_CLERK_SIGN_IN_URL ?? null,
    },
    app: {
      url: process.env.NEXT_PUBLIC_APP_URL ?? null,
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
  });
}
