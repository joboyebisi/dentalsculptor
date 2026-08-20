import { prisma } from "@/lib/prisma";
import { createClient } from "@/lib/supabase/server";
import type { UserRole } from "@/generated/prisma/client";
import { isUiPreviewMode, PREVIEW_USER } from "@/lib/preview-mode";

export async function getAuthUser() {
  if (isUiPreviewMode()) {
    return PREVIEW_USER;
  }

  const supabase = await createClient();
  const {
    data: { user: supabaseUser },
  } = await supabase.auth.getUser();

  if (!supabaseUser) return null;

  let user = await prisma.user.findUnique({ where: { supabaseId: supabaseUser.id } });

  if (!user) {
    const meta = supabaseUser.user_metadata ?? {};
    user = await prisma.user.create({
      data: {
        supabaseId: supabaseUser.id,
        email: supabaseUser.email ?? "",
        name:
          (meta.full_name as string | undefined) ??
          (meta.name as string | undefined) ??
          supabaseUser.email?.split("@")[0] ??
          "User",
        avatarUrl: (meta.avatar_url as string | undefined) ?? null,
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
