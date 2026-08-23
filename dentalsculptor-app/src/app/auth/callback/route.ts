import { NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { resolvePostAuthPath } from "@/lib/post-auth-redirect";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next");

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      const user = await getAuthUser();
      const destination = resolvePostAuthPath(user, next);
      return NextResponse.redirect(`${origin}${destination}`);
    }

    console.error("[auth/callback]", error.message);
    const reason = encodeURIComponent(error.message.slice(0, 200));
    return NextResponse.redirect(
      `${origin}/sign-in?error=auth_callback_failed&reason=${reason}`
    );
  }

  return NextResponse.redirect(`${origin}/sign-in?error=auth_callback_failed`);
}
