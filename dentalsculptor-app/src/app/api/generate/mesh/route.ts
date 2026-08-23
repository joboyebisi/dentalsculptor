import { createHash, randomBytes, randomUUID, timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { isUiPreviewMode } from "@/lib/preview-mode";
import { generateMeshFromImage, isFalConfigured } from "@/lib/fal-mesh-generator";
import { generateDentalMeshFromImage } from "@/lib/model-generator";
import { trackResearchEvent } from "@/lib/research-events";
import {
  createModalGenerationJob,
  generateMeshViaModal,
  getMlMeshProvider,
  isModalAsyncS3Enabled,
} from "@/lib/ml-provider";
import { prisma } from "@/lib/prisma";
import { generationErrorMessage, logGeneration } from "@/lib/generation-log";
import { isModalAsyncDisabledError, modalAsyncDisabledHint } from "@/lib/generation-errors";

/** Hobby plan max is 300s. Async path returns 202 quickly; sync fallback may still timeout on long cold starts. */
export const maxDuration = 300;

function hasValidResearchAccessCode(value: FormDataEntryValue | null): boolean {
  const expected = process.env.RESEARCH_GENERATION_ACCESS_CODE ?? "";
  const supplied = typeof value === "string" ? value.trim() : "";
  if (!expected || !supplied) return false;
  const expectedBytes = Buffer.from(expected);
  const suppliedBytes = Buffer.from(supplied);
  return (
    expectedBytes.length === suppliedBytes.length &&
    timingSafeEqual(expectedBytes, suppliedBytes)
  );
}

export async function POST(req: NextRequest) {
  const user = await getAuthUser();
  const formData = await req.formData();
  if (
    !user &&
    !isUiPreviewMode() &&
    !hasValidResearchAccessCode(formData.get("accessCode"))
  ) {
    return NextResponse.json(
      {
        error:
          "Open your educator invite link (it includes ?invite=...) or sign in to generate.",
      },
      { status: 403 }
    );
  }

  const image = formData.get("image") as File | null;
  const projectId = (formData.get("projectId") as string) || undefined;
  const qualityRaw = (formData.get("quality") as string) || "";
  const quality =
    qualityRaw === "preview" || qualityRaw === "final" || qualityRaw === "standard"
      ? qualityRaw
      : isModalAsyncS3Enabled()
        ? "preview"
        : "preview";
  const seedValue = formData.get("seed");
  const seed =
    typeof seedValue === "string" && /^\d+$/.test(seedValue)
      ? Number(seedValue)
      : undefined;

  if (!image?.size) {
    return NextResponse.json({ error: "Image file is required." }, { status: 400 });
  }

  const provider = getMlMeshProvider();
  const traceId = randomUUID();
  logGeneration({
    traceId,
    phase: "start",
    provider,
    quality,
    imageBytes: image.size,
    asyncS3: isModalAsyncS3Enabled(),
  });

  if (provider === "mock") {
    const meshData = generateDentalMeshFromImage(800, 600);
    return NextResponse.json({
      source: "mock",
      meshData,
      message: "Set FAL_KEY or deploy Modal (ML_MESH_PROVIDER=modal) for real generation.",
    });
  }

  try {
    const t0 = Date.now();
    if (provider === "modal" && isModalAsyncS3Enabled()) {
      if (projectId && !user) {
        return NextResponse.json(
          { error: "Sign in is required to attach generation to a project." },
          { status: 401 }
        );
      }
      if (projectId && user) {
        const ownsProject = await prisma.project.count({
          where: { id: projectId, ownerId: user.id },
        });
        if (!ownsProject) {
          return NextResponse.json({ error: "Project not found." }, { status: 404 });
        }
      }

      const jobId = randomUUID();
      const jobToken = randomBytes(32).toString("base64url");
      const jobTokenHash = createHash("sha256").update(jobToken).digest("hex");
      await prisma.generationJob.create({
        data: {
          id: jobId,
          ownerId: user?.id,
          projectId,
          quality,
          jobTokenHash,
        },
      });
      try {
        await createModalGenerationJob(image, jobId, { quality, seed, traceId });
      } catch (error) {
        const errMsg = error instanceof Error ? error.message : "Modal submission failed.";
        logGeneration({
          traceId,
          phase: "failed",
          provider: "modal",
          jobId,
          error: errMsg,
          upstream: "createModalGenerationJob",
        });
        if (isModalAsyncDisabledError(errMsg)) {
          logGeneration({
            traceId,
            phase: "failed",
            provider: "modal",
            jobId,
            error: errMsg,
            detail: modalAsyncDisabledHint(),
          });
          await prisma.generationJob.delete({ where: { id: jobId } }).catch(() => undefined);
          return NextResponse.json(
            {
              error:
                "Generation service is misconfigured. The admin needs to redeploy Modal with async S3 enabled.",
              traceId,
              detail: modalAsyncDisabledHint(),
            },
            { status: 503 }
          );
        }
        await prisma.generationJob.update({
          where: { id: jobId },
          data: {
            status: "FAILED",
            stage: "failed",
            progress: 100,
            error: errMsg,
            completedAt: new Date(),
          },
        });
        throw error;
      }
      logGeneration({
        traceId,
        phase: "accepted",
        provider: "modal",
        jobId,
        durationMs: Date.now() - t0,
        mode: "async",
      });
      return NextResponse.json(
        {
          source: "modal",
          requestId: jobId,
          jobId,
          jobToken,
          status: "queued",
          stage: "queued",
          progress: 0,
        },
        { status: 202 }
      );
    }

    const result =
      provider === "modal"
        ? await generateMeshViaModal(image, user?.id ?? "anonymous", {
            quality,
            seed,
            traceId,
          })
        : await generateMeshFromImage(image);

    logGeneration({
      traceId,
      phase: "complete",
      provider,
      durationMs: Date.now() - t0,
      format: result.format,
    });

    if (user && projectId && !isUiPreviewMode()) {
      await trackResearchEvent({
        userId: user.id,
        projectId,
        eventType: "MODEL_GENERATED",
        metadata: {
          provider,
          format: result.format,
          requestId: result.requestId,
        },
      });
    }

    return NextResponse.json({
      source: provider,
      modelUrl: result.modelUrl,
      thumbnailUrl: result.thumbnailUrl,
      textureUrl: result.textureUrl,
      mtlUrl: result.mtlUrl,
      format: result.format,
      requestId: result.requestId,
    });
  } catch (error) {
    const errMsg = error instanceof Error ? error.message : String(error);
    logGeneration({
      traceId,
      phase: "failed",
      provider,
      error: errMsg,
      detail: isModalAsyncDisabledError(errMsg) ? modalAsyncDisabledHint() : undefined,
    });

    const allowFallback =
      process.env.ML_ALLOW_FAL_FALLBACK === "true" && isFalConfigured();
    if (provider === "modal" && allowFallback) {
      console.warn("[generate/mesh] primary generation failed — trying configured fallback");
      try {
        const result = await generateMeshFromImage(image);
        return NextResponse.json({ source: "fal", ...result, fallback: true });
      } catch (falErr) {
        console.error("[generate/mesh] fal fallback failed", falErr);
      }
    }

    const message =
      provider === "modal"
        ? error instanceof Error && error.message.startsWith("The tooth could not be isolated")
          ? error.message
          : generationErrorMessage(error, traceId)
        : error instanceof Error
          ? error.message
          : "Mesh generation failed.";
    return NextResponse.json({ error: message, traceId }, { status: 500 });
  }
}
