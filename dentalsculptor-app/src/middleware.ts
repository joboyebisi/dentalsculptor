import { NextResponse, type NextRequest } from "next/server";

const isPreviewMode = process.env.UI_PREVIEW_MODE === "true";

export default async function middleware(req: NextRequest) {
  if (isPreviewMode) {
    return NextResponse.next();
  }

  const { clerkMiddleware, createRouteMatcher } = await import("@clerk/nextjs/server");

  const isPublicRoute = createRouteMatcher([
    "/",
    "/sign-in(.*)",
    "/sign-up(.*)",
    "/api/webhooks(.*)",
    "/api/generate/mesh",
    "/api/generate/jobs(.*)",
    "/api/ml/warm",
    "/api/models/proxy",
    "/community(.*)",
  ]);

  const handler = clerkMiddleware(async (auth, request) => {
    if (!isPublicRoute(request)) {
      await auth.protect();
    }
    return NextResponse.next();
  });

  return handler(req, {} as never);
}

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
