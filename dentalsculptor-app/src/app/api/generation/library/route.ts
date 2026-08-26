import { NextResponse } from "next/server";
import { loadGenerationLibraryManifest } from "@/lib/generation-library";

export async function GET() {
  try {
    const manifest = await loadGenerationLibraryManifest();
    return NextResponse.json(manifest);
  } catch (error) {
    console.error("[generation/library]", error);
    return NextResponse.json({ version: 1, items: [] });
  }
}
