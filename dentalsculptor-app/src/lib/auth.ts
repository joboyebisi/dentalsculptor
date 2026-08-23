import { prisma } from "@/lib/prisma";
import { createClient } from "@/lib/supabase/server";
import { Prisma, type UserRole } from "@/generated/prisma/client";
import { isUiPreviewMode, PREVIEW_USER } from "@/lib/preview-mode";
import type { User as SupabaseUser } from "@supabase/supabase-js";

function profileFromSupabaseUser(supabaseUser: SupabaseUser) {
  const meta = supabaseUser.user_metadata ?? {};
  const email =
    supabaseUser.email?.trim() ||
    `${supabaseUser.id}@users.dentalsculptor.local`;

  return {
    supabaseId: supabaseUser.id,
    email,
    name:
      (meta.full_name as string | undefined) ??
      (meta.name as string | undefined) ??
      supabaseUser.email?.split("@")[0] ??
      "User",
    avatarUrl: (meta.avatar_url as string | undefined) ?? null,
  };
}

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

  if (!user && supabaseUser.email) {
    const existingByEmail = await prisma.user.findUnique({
      where: { email: supabaseUser.email.trim() },
    });

    if (existingByEmail) {
      const profile = profileFromSupabaseUser(supabaseUser);
      user = await prisma.user.update({
        where: { id: existingByEmail.id },
        data: {
          supabaseId: profile.supabaseId,
          name: existingByEmail.name ?? profile.name,
          avatarUrl: existingByEmail.avatarUrl ?? profile.avatarUrl,
        },
      });
    }
  }

  if (!user) {
    const profile = profileFromSupabaseUser(supabaseUser);

    try {
      user = await prisma.user.create({ data: profile });
    } catch (error) {
      if (
        error instanceof Prisma.PrismaClientKnownRequestError &&
        error.code === "P2002" &&
        supabaseUser.email
      ) {
        user = await prisma.user.update({
          where: { email: supabaseUser.email.trim() },
          data: {
            supabaseId: supabaseUser.id,
            name: profile.name,
            avatarUrl: profile.avatarUrl,
          },
        });
      } else {
        throw error;
      }
    }
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
