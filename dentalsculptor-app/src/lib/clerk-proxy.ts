/** Derive Clerk FAPI proxy URL for *.vercel.app (required for pk_test_ on Vercel). */
export function resolveClerkProxyUrl(): string | undefined {
  const explicit = process.env.NEXT_PUBLIC_CLERK_PROXY_URL?.trim();
  if (explicit) {
    return explicit.replace(/\/$/, "");
  }

  const host =
    process.env.VERCEL_PROJECT_PRODUCTION_URL?.trim() ||
    process.env.VERCEL_URL?.trim();
  if (!host) {
    return undefined;
  }

  const normalized = host.replace(/^https?:\/\//, "").split("/")[0] ?? "";
  if (!normalized.endsWith(".vercel.app")) {
    return undefined;
  }

  return `https://${normalized}/__clerk`;
}

export function clerkKeyDiagnostics() {
  const pk = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "";
  const sk = process.env.CLERK_SECRET_KEY ?? "";
  const pkType = pk.startsWith("pk_live_")
    ? "production"
    : pk.startsWith("pk_test_")
      ? "development"
      : "missing";
  const skType = sk.startsWith("sk_live_")
    ? "production"
    : sk.startsWith("sk_test_")
      ? "development"
      : "missing";

  return {
    hasPublishableKey: pk.startsWith("pk_"),
    hasSecretKey: sk.startsWith("sk_"),
    keyType: pkType,
    secretKeyType: skType,
    keyPairMatch: pkType !== "missing" && pkType === skType,
    proxyUrl: resolveClerkProxyUrl() ?? null,
    signInUrl: process.env.NEXT_PUBLIC_CLERK_SIGN_IN_URL ?? null,
  };
}
