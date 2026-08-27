const SESSION_KEY = "ds_pending_landing_project";

export type PendingNextStep = "download" | "publish" | "editor" | "case-wizard";

export interface PendingLandingProject {
  modelUrl: string;
  modelKey?: string;
  thumbnailUrl?: string;
  mtlUrl?: string;
  format?: string;
  sourceFileName: string;
  imageDataUrl: string;
  createdAt: number;
  /** After auth: open editor directly or case template wizard first. */
  nextStep?: PendingNextStep;
  caseTemplateId?: string;
}

export async function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new Error("Could not read image file."));
    reader.readAsDataURL(file);
  });
}

export function savePendingLandingProject(
  data: Omit<PendingLandingProject, "createdAt">
): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(
    SESSION_KEY,
    JSON.stringify({ ...data, createdAt: Date.now() })
  );
}

export function getPendingLandingProject(): PendingLandingProject | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as PendingLandingProject;
  } catch {
    return null;
  }
}

export function clearPendingLandingProject(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(SESSION_KEY);
}

export function dataUrlToFile(dataUrl: string, filename: string): File {
  const [header, base64] = dataUrl.split(",");
  const mime = header.match(/:(.*?);/)?.[1] ?? "image/jpeg";
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new File([bytes], filename, { type: mime });
}
