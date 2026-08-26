export type GenerationLibraryItem = {
  id: string;
  title: string;
  toothType?: "incisor" | "canine" | "premolar" | "molar";
  fdiHint?: string;
  path: string;
  credit?: string;
};

export type GenerationLibraryManifest = {
  version: number;
  description?: string;
  items: GenerationLibraryItem[];
};

export async function loadGenerationLibraryManifest(): Promise<GenerationLibraryManifest> {
  const { readFile } = await import("node:fs/promises");
  const { join } = await import("node:path");
  const manifestPath = join(process.cwd(), "public", "generation-library", "manifest.json");
  const raw = await readFile(manifestPath, "utf8");
  return JSON.parse(raw) as GenerationLibraryManifest;
}
