"use client";

import Link from "next/link";
import { SignInButton, SignUpButton, useAuth } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { AppLogo } from "@/components/brand/app-logo";

const isPreview = process.env.NEXT_PUBLIC_UI_PREVIEW_MODE === "true";

export function PublicNav() {
  if (isPreview) return <PublicNavPreview />;
  return <PublicNavClerk />;
}

function PublicNavPreview() {
  return (
    <nav className="sticky top-0 z-50 flex h-14 w-full items-center justify-between border-b border-border-subtle bg-panel-bg/90 px-margin-page backdrop-blur-md">
      <NavBrand />
      <div className="flex items-center gap-2">
        <Link href="/editor/preview-project-1">
          <Button variant="ghost" size="sm">Editor</Button>
        </Link>
        <Link href="/dashboard">
          <Button size="sm">App</Button>
        </Link>
      </div>
    </nav>
  );
}

function PublicNavClerk() {
  const { isSignedIn } = useAuth();
  return (
    <nav className="sticky top-0 z-50 flex h-14 w-full items-center justify-between border-b border-border-subtle bg-panel-bg/90 px-margin-page backdrop-blur-md">
      <NavBrand />
      <div className="flex items-center gap-3">
        {!isSignedIn ? (
          <>
            <SignInButton mode="modal">
              <Button variant="ghost" size="sm">Sign in</Button>
            </SignInButton>
            <SignUpButton mode="modal">
              <Button size="sm">Register</Button>
            </SignUpButton>
          </>
        ) : (
          <Link href="/dashboard">
            <Button size="sm">Dashboard</Button>
          </Link>
        )}
      </div>
    </nav>
  );
}

function NavBrand() {
  return (
    <div className="flex items-center gap-4">
      <AppLogo size="sm" />
      <div className="hidden items-center gap-1 md:flex">
        <Link href="#workbench" className="px-3 py-2 text-body-sm text-on-surface-variant hover:text-primary-container">
          Try it
        </Link>
        <Link href="#how-it-works" className="px-3 py-2 text-body-sm text-on-surface-variant hover:text-primary-container">
          How it works
        </Link>
        <Link href="#community" className="px-3 py-2 text-body-sm text-on-surface-variant hover:text-primary-container">
          Community
        </Link>
        <Link href="#research" className="px-3 py-2 text-body-sm text-on-surface-variant hover:text-primary-container">
          Research
        </Link>
        <Link href="/editor/preview-project-1" className="px-3 py-2 text-body-sm text-on-surface-variant hover:text-primary-container">
          Editor
        </Link>
      </div>
    </div>
  );
}

export function PublicFooter() {
  return (
    <footer className="border-t border-border-subtle bg-panel-bg">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-margin-page py-10 md:flex-row">
        <AppLogo size="sm" href="/" />
        <p className="text-center text-body-sm text-on-surface-variant md:text-left">
          Academic research project — AI-aided dental education authoring.
        </p>
        <p className="text-body-sm text-on-surface-variant">
          © {new Date().getFullYear()} DentalSculptor
        </p>
      </div>
    </footer>
  );
}
