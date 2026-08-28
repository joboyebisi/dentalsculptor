import { NextRequest, NextResponse } from "next/server";
import {
  guessModelContentType,
  isAllowedModelAssetUrl,
} from "@/lib/model-asset-url";
import { extractStorageKeyFromUrl } from "@/lib/storage";

export const maxDuration = 60;

export async function GET(req: NextRequest) {
  const rawUrl = req.nextUrl.searchParams.get("url");
  if (!rawUrl) {
    return NextResponse.json({ error: "Missing url parameter." }, { status: 400 });
  }

  let target: URL;
  try {
    target = new URL(rawUrl);
  } catch {
    return NextResponse.json({ error: "Invalid url." }, { status: 400 });
  }

  if (target.protocol !== "https:" && target.protocol !== "http:") {
    return NextResponse.json({ error: "Unsupported protocol." }, { status: 400 });
  }

  if (!isAllowedModelAssetUrl(target.toString())) {
    return NextResponse.json({ error: "URL host not allowed." }, { status: 403 });
  }

  try {
    const upstream = await fetch(target.toString(), {
      headers: { "User-Agent": "DentalSculptor/1.0" },
      cache: "no-store",
      signal: AbortSignal.timeout(120_000),
    });

    if (!upstream.ok) {
      const storageKey = extractStorageKeyFromUrl(target.toString());
      console.error(
        "[models/proxy] upstream failed",
        upstream.status,
        storageKey ? `(storage key: ${storageKey})` : target.hostname
      );
      return NextResponse.json(
        {
          error:
            upstream.status === 403
              ? "Model link expired. Re-open the project to refresh."
              : `Upstream returned ${upstream.status}`,
        },
        { status: 502 }
      );
    }

    const contentType =
      upstream.headers.get("content-type") ??
      guessModelContentType(target.pathname);
    const contentLength = upstream.headers.get("content-length");

    return new NextResponse(upstream.body, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        ...(contentLength ? { "Content-Length": contentLength } : {}),
        "Cache-Control": "public, max-age=3600",
        "Access-Control-Allow-Origin": "*",
      },
    });
  } catch (error) {
    console.error("[models/proxy]", error);
    return NextResponse.json({ error: "Failed to fetch model asset." }, { status: 502 });
  }
}
