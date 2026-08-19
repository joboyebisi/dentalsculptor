import type { SerializedCameraState } from "@/lib/camera-utils";

export type EditOperation = "add" | "remove" | "replace";

export type EditJobStatus = "idle" | "previewing" | "queued" | "running" | "completed" | "failed";

export interface EditJobRequest {
  projectId: string;
  instruction: string;
  operation: EditOperation;
  sourceModelUrl: string;
  maskBlob?: Blob;
  referenceImageBlob?: Blob;
  camera?: SerializedCameraState;
  sourceRevisionId?: string;
  selectedPartIds?: string[];
}
