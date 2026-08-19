import { clerkMiddleware } from "@clerk/nextjs/server";
import { resolveClerkProxyUrl } from "@/lib/clerk-proxy";

/**
 * pk_test_ on *.vercel.app needs FAPI proxy — auto-derived from VERCEL_PROJECT_PRODUCTION_URL.
 * Override with NEXT_PUBLIC_CLERK_PROXY_URL=https://your-app.vercel.app/__clerk
 */
const proxyUrl = resolveClerkProxyUrl();

export default clerkMiddleware(
  proxyUrl
    ? {
        proxyUrl,
        frontendApiProxy: { enabled: true },
      }
    : {}
);

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
    "/__clerk/(.*)",
  ],
};
