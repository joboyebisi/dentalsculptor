import { NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";

export const maxDuration = 30;

/** Verify Modal Nano3D edit + job-status endpoints (educator/admin diagnostic). */
export async function GET() {
  const user = await getAuthUser();
  if (!user) {
    return NextResponse.json({ error: "Sign in required." }, { status: 401 });
  }

  const editUrl = process.env.MODAL_EDIT_URL ?? "";
  const statusUrl = process.env.MODAL_JOB_STATUS_URL ?? "";
  const webhookSecret = process.env.MODAL_WEBHOOK_SECRET ?? "";

  const result: Record<string, unknown> = {
    configured: {
      MODAL_EDIT_URL: Boolean(editUrl),
      MODAL_JOB_STATUS_URL: Boolean(statusUrl),
      MODAL_WEBHOOK_SECRET: Boolean(webhookSecret),
    },
    editUrlHost: editUrl ? new URL(editUrl).host : null,
    jobStatusUrlHost: statusUrl ? new URL(statusUrl).host : null,
    probes: {} as Record<string, unknown>,
  };

  if (statusUrl && webhookSecret) {
    const probeId = "__health_probe__";
    const t0 = Date.now();
    try {
      const res = await fetch(`${statusUrl}?jobId=${encodeURIComponent(probeId)}`, {
        headers: { Authorization: `Bearer ${webhookSecret}` },
        signal: AbortSignal.timeout(15000),
      });
      const raw = await res.text();
      let body: unknown = null;
      if (raw.trim()) {
        try {
          body = JSON.parse(raw);
        } catch {
          body = raw.slice(0, 120);
        }
      }
      result.probes = {
        jobStatus: {
          ok: res.status === 404 || res.ok,
          httpStatus: res.status,
          latencyMs: Date.now() - t0,
          note:
            res.status === 404
              ? "Endpoint live — probe job not found (expected)."
              : res.ok
                ? "Endpoint responded."
                : "Unexpected status — check MODAL_WEBHOOK_SECRET and URL.",
          body,
        },
      };
    } catch (err) {
      result.probes = {
        jobStatus: {
          ok: false,
          error: err instanceof Error ? err.message : String(err),
          latencyMs: Date.now() - t0,
        },
      };
    }
  }

  const probes = result.probes as { jobStatus?: { ok?: boolean } };
  const allConfigured =
    Boolean(editUrl) && Boolean(statusUrl) && Boolean(webhookSecret);
  const jobStatusOk = probes.jobStatus?.ok !== false;

  return NextResponse.json({
    ...result,
    ready: allConfigured && (statusUrl ? jobStatusOk : allConfigured),
    nano3dNote:
      "POST /api/projects/{id}/edit-jobs submits edits. Completed jobs return modelUrl + Accept revision banner. CPU v1 deforms masked vertices; check maskedVertexRatio in logs.",
  });
}
