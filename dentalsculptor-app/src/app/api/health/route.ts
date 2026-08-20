import { NextResponse } from "next/server";

/** Lightweight deploy diagnostics — safe to expose (no secrets). */
export async function GET() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
  const hasAnonKey = Boolean(process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY);

  return NextResponse.json({
    ok: true,
    timestamp: new Date().toISOString(),
    auth: {
      provider: "supabase",
      supabaseConfigured: Boolean(supabaseUrl && hasAnonKey),
      supabaseHost: supabaseUrl ? new URL(supabaseUrl).hostname : null,
    },
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
  });
}
