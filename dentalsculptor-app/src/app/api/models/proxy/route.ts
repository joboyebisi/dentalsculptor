import { NextRequest, NextResponse } from "next/server";
import {
  guessModelContentType,
  isAllowedModelAssetUrl,
} from "@/lib/model-asset-url";

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
    });

    if (!upstream.ok) {
      return NextResponse.json(
        { error: `Upstream returned ${upstream.status}` },
        { status: 502 }
      );
    }

    const body = await upstream.arrayBuffer();
    const contentType =
      upstream.headers.get("content-type") ??
      guessModelContentType(target.pathname);

    return new NextResponse(body, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "public, max-age=86400",
        "Access-Control-Allow-Origin": "*",
      },
    });
  } catch (error) {
    console.error("[models/proxy]", error);
    return NextResponse.json({ error: "Failed to fetch model asset." }, { status: 502 });
  }
}
