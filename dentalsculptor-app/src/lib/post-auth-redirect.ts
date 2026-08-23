export type AuthGateUser = {
  consentAccepted: boolean;
  onboardingCompleted: boolean;
};

/** Where to send the user after sign-in based on profile completion. */
export function resolvePostAuthPath(
  user: AuthGateUser | null | undefined,
  requestedNext?: string | null
): string {
  if (!user) return "/sign-in";
  if (!user.consentAccepted) return "/consent";
  if (!user.onboardingCompleted) return "/onboarding";

  const next =
    requestedNext?.startsWith("/") &&
    requestedNext !== "/consent" &&
    requestedNext !== "/onboarding"
      ? requestedNext
      : null;

  return next ?? "/dashboard";
}
