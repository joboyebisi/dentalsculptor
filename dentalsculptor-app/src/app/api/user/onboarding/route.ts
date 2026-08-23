import { NextRequest, NextResponse } from "next/server";
import { getAuthUser, isResearcherOrAdmin } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import type { UserRole } from "@/generated/prisma/client";
import { ONBOARDING_ROLES } from "@/lib/constants";

const ALLOWED_ONBOARDING_ROLES = new Set<string>(
  ONBOARDING_ROLES.map((r) => r.value)
);

export async function POST(req: NextRequest) {
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await req.json();
  const role = body.role as UserRole;

  if (!ALLOWED_ONBOARDING_ROLES.has(role)) {
    return NextResponse.json(
      { error: "Invalid role. Choose Educator or Student." },
      { status: 400 }
    );
  }

  await prisma.user.update({
    where: { id: user.id },
    data: {
      role: body.role as UserRole,
      institution: body.institution,
      department: body.department,
      country: body.country,
      onboardingCompleted: true,
    },
  });

  return NextResponse.json({ success: true });
}
