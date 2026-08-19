"use client";

import { KeyRound, LogIn } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

interface ResearchInviteCalloutProps {
  hasInvite: boolean;
  isSignedIn: boolean;
}

/** Shown below Generate — explains invite-link access for anonymous pilot users. */
export function ResearchInviteCallout({ hasInvite, isSignedIn }: ResearchInviteCalloutProps) {
  if (isSignedIn) return null;

  if (hasInvite) {
    return (
      <div
        role="status"
        className="mt-3 rounded-lg border border-primary-container/30 bg-primary-container/10 px-4 py-3"
      >
        <div className="flex gap-3">
          <KeyRound className="mt-0.5 h-4 w-4 shrink-0 text-primary-container" aria-hidden />
          <p className="text-body-sm text-on-surface">
            <span className="font-medium">Educator invite active.</span> You can generate from this
            link before creating an account. Save your project by signing up after the model
            appears.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      role="note"
      className="mt-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3"
    >
      <div className="flex gap-3">
        <KeyRound className="mt-0.5 h-4 w-4 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden />
        <div className="space-y-2 text-body-sm">
          <p className="font-medium text-on-surface">Invite link required</p>
          <p className="text-on-surface-variant">
            Open the personal link shared with you — it includes your invite code in the URL
            (for example{" "}
            <code className="rounded bg-surface-container px-1 py-0.5 text-xs">
              ?invite=your-code
            </code>
            ). That link unlocks generation before sign-up.
          </p>
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <Link href="/sign-in">
              <Button type="button" variant="outline" size="sm">
                <LogIn className="mr-1.5 h-3.5 w-3.5" />
                Sign in instead
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
