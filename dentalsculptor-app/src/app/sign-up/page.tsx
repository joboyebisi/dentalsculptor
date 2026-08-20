import { AuthForm } from "@/components/auth/auth-form";

export default async function SignUpPage({
  searchParams,
}: {
  searchParams: Promise<{ redirect_url?: string }>;
}) {
  const params = await searchParams;

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <AuthForm mode="sign-up" redirectUrl={params.redirect_url ?? null} />
    </div>
  );
}
