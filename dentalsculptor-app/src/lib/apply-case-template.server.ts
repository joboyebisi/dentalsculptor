/**
 * Server-only: persist CaseRecipe to Postgres via Prisma.
 */

import { getCaseTemplate } from "@/lib/case-templates";
import { buildCaseProjectTitle } from "@/lib/case-project-title";
import {
  buildCaseRecipe,
  buildEditPromptFromRecipe,
  formatInstructionsFromRecipe,
  validateClinicalParameters,
  type ApplyCaseTemplateInput,
} from "@/lib/case-recipe-utils";
import { prisma } from "@/lib/prisma";

export async function applyCaseTemplateToProject(
  projectId: string,
  ownerId: string,
  input: ApplyCaseTemplateInput
) {
  const template = getCaseTemplate(input.templateId);
  if (!template) {
    throw new Error("Unknown case template.");
  }

  const validationError = validateClinicalParameters(
    template.clinicalParameterFields,
    input.clinicalParameters
  );
  if (validationError) {
    throw new Error(validationError);
  }

  const recipe = buildCaseRecipe(
    template,
    input.clinicalParameters,
    input.promptRefinement
  );

  const instructions = formatInstructionsFromRecipe(recipe, template);
  const hints = template.studentHints.join("\n• ");
  const description = template.shortDescription;
  const projectTitle = buildCaseProjectTitle(template, input.clinicalParameters);

  const existing = await prisma.project.findFirst({
    where: { id: projectId, ownerId },
    include: {
      learningObjectives: true,
      assessments: true,
      versions: { where: { label: "case-recipe" }, orderBy: { version: "desc" }, take: 1 },
    },
  });

  if (!existing) {
    throw new Error("Project not found.");
  }

  const nextVersion = (existing.versions[0]?.version ?? 0) + 1;

  await prisma.$transaction(async (tx) => {
    if (existing.learningObjectives.length === 0) {
      await tx.learningObjective.createMany({
        data: template.learningObjectives.map((title, order) => ({
          projectId,
          title,
          order,
        })),
      });
    }

    if (existing.assessments.length === 0) {
      await tx.assessment.createMany({
        data: template.assessmentPrompts.map((question, order) => ({
          projectId,
          question,
          type: "short_answer",
          order,
        })),
      });
    }

    await tx.project.update({
      where: { id: projectId },
      data: {
        title: projectTitle,
        description,
        instructions,
        hints: hints ? `• ${hints}` : undefined,
        category: `case:${template.id}`,
      },
    });

    await tx.projectVersion.create({
      data: {
        projectId,
        version: nextVersion,
        label: "case-recipe",
        snapshot: recipe as object,
      },
    });
  });

  return { recipe, template, editPrompt: buildEditPromptFromRecipe(recipe, template), projectTitle };
}
