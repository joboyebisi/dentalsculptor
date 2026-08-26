import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import {
  applyCaseTemplateToProject,
} from "@/lib/apply-case-template.server";
import type { ApplyCaseTemplateInput } from "@/lib/case-recipe-utils";
import { trackResearchEvent } from "@/lib/research-events";
import { ownershipMetricsFromTemplate } from "@/lib/case-templates";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id: projectId } = await params;
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = (await req.json()) as ApplyCaseTemplateInput;

  if (!body.templateId) {
    return NextResponse.json({ error: "templateId is required." }, { status: 400 });
  }

  try {
    const result = await applyCaseTemplateToProject(projectId, user.id, body);

    await trackResearchEvent({
      userId: user.id,
      projectId,
      eventType: "LEARNING_OBJECTIVE_CREATED",
      metadata: {
        ...ownershipMetricsFromTemplate(body.templateId, false),
        clinicalFieldCount: Object.keys(body.clinicalParameters ?? {}).length,
      },
    });

    return NextResponse.json({
      ok: true,
      recipe: result.recipe,
      editPrompt: result.editPrompt,
      exportRecommendation: result.template.exportRecommendation,
      project: {
        title: result.projectTitle,
        description: result.template.shortDescription,
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to apply template.";
    return NextResponse.json({ error: message }, { status: 400 });
  }
}
