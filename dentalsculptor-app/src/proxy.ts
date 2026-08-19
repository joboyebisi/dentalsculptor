import { clerkMiddleware } from "@clerk/nextjs/server";

/**
 * Next.js 16: use proxy.ts (not middleware.ts).
 *
 * Dev Clerk keys (pk_test_) on *.vercel.app do NOT get auto-proxy — without
 * frontendApiProxy the __clerk_handshake redirect 500s ("handshake without redirect").
 * Set NEXT_PUBLIC_CLERK_PROXY_URL=https://YOUR_APP.vercel.app/__clerk on Vercel.
 */
export default clerkMiddleware({
  frontendApiProxy: {
    enabled: true,
  },
});

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
    "/__clerk/(.*)",
  ],
};
