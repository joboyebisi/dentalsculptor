"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createClient } from "@/lib/supabase/client";
import { AppLogo } from "@/components/brand/app-logo";

type AuthMode = "sign-in" | "sign-up";

const OAUTH_PROVIDERS = [
  { id: "google" as const, label: "Google" },
  { id: "azure" as const, label: "Microsoft" },
  { id: "facebook" as const, label: "Facebook" },
];

function resolveRedirectPath(redirectUrl: string | null, fallback: string) {
  if (!redirectUrl || !redirectUrl.startsWith("/")) return fallback;
  return redirectUrl;
}

export function AuthForm({
  mode,
  redirectUrl,
}: {
  mode: AuthMode;
  redirectUrl: string | null;
}) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const afterAuthPath = resolveRedirectPath(redirectUrl, "/consent");
  const isSignUp = mode === "sign-up";

  async function handleEmailAuth(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);

    const supabase = createClient();

    if (isSignUp) {
      const { data, error: signUpError } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { full_name: name.trim() || undefined },
          emailRedirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(afterAuthPath)}`,
        },
      });

      if (signUpError) {
        setError(signUpError.message);
        setBusy(false);
        return;
      }

      if (data.session) {
        router.push(afterAuthPath);
        router.refresh();
        return;
      }

      setMessage("Check your email to confirm your account, then sign in.");
      setBusy(false);
      return;
    }

    const { error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (signInError) {
      setError(signInError.message);
      setBusy(false);
      return;
    }

    router.push(afterAuthPath);
    router.refresh();
  }

  async function handleOAuth(provider: (typeof OAUTH_PROVIDERS)[number]["id"]) {
    setBusy(true);
    setError(null);

    const supabase = createClient();
    const { error: oauthError } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(afterAuthPath)}`,
      },
    });

    if (oauthError) {
      setError(oauthError.message);
      setBusy(false);
    }
  }

  return (
    <div className="w-full max-w-md space-y-6">
      <div className="flex flex-col items-center gap-3 text-center">
        <AppLogo size="md" href="/" />
        <h1 className="text-headline-md font-semibold text-text-main">
          {isSignUp ? "Create your account" : "Sign in"}
        </h1>
        <p className="text-body-sm text-on-surface-variant">
          {isSignUp
            ? "Join DentalSculptor to save projects and access the workspace."
            : "Welcome back — continue to your teaching workspace."}
        </p>
      </div>

      <div className="rounded-xl border border-border-subtle bg-panel-bg p-6 shadow-sm">
        <div className="space-y-3">
          {OAUTH_PROVIDERS.map((provider) => (
            <Button
              key={provider.id}
              type="button"
              variant="outline"
              className="w-full"
              disabled={busy}
              onClick={() => handleOAuth(provider.id)}
            >
              Continue with {provider.label}
            </Button>
          ))}
        </div>

        <div className="my-6 flex items-center gap-3">
          <div className="h-px flex-1 bg-border-subtle" />
          <span className="text-body-sm text-on-surface-variant">or email</span>
          <div className="h-px flex-1 bg-border-subtle" />
        </div>

        <form onSubmit={handleEmailAuth} className="space-y-4">
          {isSignUp && (
            <div className="space-y-2">
              <Label htmlFor="name">Full name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="name"
                placeholder="Dr. Jane Smith"
              />
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
              placeholder="you@university.ac.uk"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={isSignUp ? "new-password" : "current-password"}
              required
              minLength={8}
              placeholder="At least 8 characters"
            />
          </div>

          {error && (
            <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-body-sm text-destructive">
              {error}
            </p>
          )}

          {message && (
            <p className="rounded-lg border border-primary-container/30 bg-primary-container/10 px-3 py-2 text-body-sm text-on-surface">
              {message}
            </p>
          )}

          <Button type="submit" className="w-full" disabled={busy}>
            {busy ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Please wait…
              </>
            ) : isSignUp ? (
              "Create account"
            ) : (
              "Sign in"
            )}
          </Button>
        </form>
      </div>

      <p className="text-center text-body-sm text-on-surface-variant">
        {isSignUp ? (
          <>
            Already have an account?{" "}
            <Link href={`/sign-in${redirectUrl ? `?redirect_url=${encodeURIComponent(redirectUrl)}` : ""}`} className="text-primary-container hover:underline">
              Sign in
            </Link>
          </>
        ) : (
          <>
            New here?{" "}
            <Link href={`/sign-up${redirectUrl ? `?redirect_url=${encodeURIComponent(redirectUrl)}` : ""}`} className="text-primary-container hover:underline">
              Create an account
            </Link>
          </>
        )}
      </p>
    </div>
  );
}
