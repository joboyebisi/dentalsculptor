import { auth, currentUser } from "@clerk/nextjs/server";
import { prisma } from "@/lib/prisma";
import type { UserRole } from "@/generated/prisma/client";
import { isUiPreviewMode, PREVIEW_USER } from "@/lib/preview-mode";

export async function getAuthUser() {
  if (isUiPreviewMode()) {
    return PREVIEW_USER;
  }

  const { userId } = await auth();
  if (!userId) return null;

  const clerkUser = await currentUser();
  if (!clerkUser) return null;

  let user = await prisma.user.findUnique({ where: { clerkId: userId } });

  if (!user) {
    user = await prisma.user.create({
      data: {
        clerkId: userId,
        email: clerkUser.emailAddresses[0]?.emailAddress ?? "",
        name: clerkUser.fullName ?? clerkUser.firstName ?? "User",
        avatarUrl: clerkUser.imageUrl,
      },
    });
  }

  return user;
}

export async function requireAuthUser() {
  const user = await getAuthUser();
  if (!user) throw new Error("Unauthorized");
  return user;
}

export async function requireRole(roles: UserRole[]) {
  const user = await requireAuthUser();
  if (!roles.includes(user.role)) throw new Error("Forbidden");
  return user;
}

export function isResearcherOrAdmin(role: UserRole) {
  return role === "RESEARCHER" || role === "ADMINISTRATOR";
}
