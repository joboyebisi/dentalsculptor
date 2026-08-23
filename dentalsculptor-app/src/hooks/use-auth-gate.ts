"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { resolvePostAuthPath } from "@/lib/post-auth-redirect";

type Gate = "consent" | "onboarding";

/**
 * Redirect returning users away from consent/onboarding if already completed.
 */
export function useAuthGate(gate: Gate) {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let cancelled = false;

    fetch("/api/user/profile")
      .then(async (res) => {
        if (cancelled) return;
        if (res.status === 401) {
          router.replace("/sign-in");
          return;
        }
        if (!res.ok) {
          setChecking(false);
          return;
        }
        const data = (await res.json()) as {
          user?: { consentAccepted: boolean; onboardingCompleted: boolean };
        };
        const user = data.user;
        if (!user) {
          router.replace("/sign-in");
          return;
        }

        const destination = resolvePostAuthPath(user);
        if (gate === "consent" && destination !== "/consent") {
          router.replace(destination);
          return;
        }
        if (gate === "onboarding" && destination !== "/onboarding") {
          router.replace(destination);
          return;
        }
        setChecking(false);
      })
      .catch(() => {
        if (!cancelled) setChecking(false);
      });

    return () => {
      cancelled = true;
    };
  }, [gate, router]);

  return { checking };
}
