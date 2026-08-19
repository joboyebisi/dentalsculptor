import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

/**
 * Clerk + Next.js 16 on Vercel: Edge middleware can crash (MIDDLEWARE_INVOCATION_FAILED).
 * Node.js runtime is required for reliable Clerk handshake on Hobby/production.
 */
export const runtime = "nodejs";

const isPublicRoute = createRouteMatcher([
  "/",
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/sign-up",
  "/sign-in",
  "/consent",
  "/onboarding",
  "/auth/continue",
  "/api/webhooks(.*)",
  "/api/generate/mesh",
  "/api/generate/jobs(.*)",
  "/api/ml/warm",
  "/api/models/proxy",
  "/community(.*)",
]);

export default clerkMiddleware(async (auth, request) => {
  if (process.env.UI_PREVIEW_MODE === "true") {
    return;
  }
  if (!isPublicRoute(request)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
