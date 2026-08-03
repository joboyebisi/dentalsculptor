import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import type { UserRole } from "@/generated/prisma/client";

export async function POST(req: NextRequest) {
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await req.json();

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
