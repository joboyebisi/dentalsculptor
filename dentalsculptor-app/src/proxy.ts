import { clerkMiddleware } from "@clerk/nextjs/server";

/**
 * Next.js 16: use proxy.ts (not middleware.ts). Clerk handshake requires /__clerk in matcher.
 * Route protection lives in layouts/API handlers — not path matching here.
 */
export default clerkMiddleware();

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
    "/__clerk/(.*)",
  ],
};
