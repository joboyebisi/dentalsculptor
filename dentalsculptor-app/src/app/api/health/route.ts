import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

/** Lightweight deploy diagnostics — safe to expose (no secrets). */
export async function GET() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
  const hasAnonKey = Boolean(process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY);
  const databaseUrl = process.env.DATABASE_URL ?? "";

  let databaseReachable = false;
  let databaseError: string | null = null;

  if (databaseUrl) {
    try {
      await prisma.$queryRaw`SELECT 1`;
      databaseReachable = true;
    } catch (error) {
      databaseError = error instanceof Error ? error.message : "unknown";
    }
  }

  return NextResponse.json({
    ok: databaseReachable,
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
      configured: Boolean(databaseUrl),
      pooler: databaseUrl.includes(":6543"),
      pgbouncer: databaseUrl.includes("pgbouncer=true"),
      reachable: databaseReachable,
      error: databaseError,
    },
    modal: {
      asyncS3: process.env.MODAL_ASYNC_S3_ENABLED === "true",
      hasGenerateUrl: Boolean(process.env.MODAL_GENERATE_ASYNC_URL),
    },
  });
}
