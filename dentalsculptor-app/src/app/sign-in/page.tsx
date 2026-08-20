import { AuthForm } from "@/components/auth/auth-form";

export default async function SignInPage({
  searchParams,
}: {
  searchParams: Promise<{ redirect_url?: string; error?: string }>;
}) {
  const params = await searchParams;

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md space-y-4">
        {params.error === "auth_callback_failed" && (
          <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-body-sm text-destructive">
            Sign-in could not be completed. Try again or use email instead.
          </p>
        )}
        <AuthForm mode="sign-in" redirectUrl={params.redirect_url ?? null} />
      </div>
    </div>
  );
}
