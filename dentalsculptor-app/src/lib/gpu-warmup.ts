import { resolveInviteCode } from "@/lib/research-invite";

const WARM_SESSION_KEY = "ds-gpu-warm-at";
const WARM_COOLDOWN_MS = 30 * 60_000;

export type GpuWarmupReason = "invite" | "upload" | "generate";

export function requestGpuWarmup(reason: GpuWarmupReason): void {
  if (typeof window === "undefined") return;

  const last = Number(sessionStorage.getItem(WARM_SESSION_KEY) ?? 0);
  if (Date.now() - last < WARM_COOLDOWN_MS) return;

  sessionStorage.setItem(WARM_SESSION_KEY, String(Date.now()));

  const invite = resolveInviteCode(null);
  const headers: Record<string, string> = { "x-gpu-warm-reason": reason };
  if (invite) headers["x-research-invite"] = invite;

  void fetch("/api/ml/warm", {
    method: "POST",
    headers,
    keepalive: true,
  }).catch(() => undefined);
}
