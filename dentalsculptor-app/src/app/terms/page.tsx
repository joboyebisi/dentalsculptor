import type { Metadata } from "next";
import Link from "next/link";
import { AppLogo } from "@/components/brand/app-logo";
import { APP_NAME } from "@/lib/constants";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: `Terms of service for ${APP_NAME} — research pilot platform for dental educators.`,
};

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border-subtle bg-panel-bg px-margin-page py-4">
        <AppLogo size="sm" href="/" />
      </header>
      <main className="mx-auto max-w-3xl px-margin-page py-10">
        <h1 className="text-display-md text-text-main">Terms of Service</h1>
        <p className="mt-2 text-body-sm text-on-surface-variant">Last updated: August 2026</p>

        <div className="prose prose-slate mt-8 max-w-none space-y-6 text-body-md text-on-surface-variant">
          <p>
            These terms apply to use of {APP_NAME} during the research pilot. Access may be
            limited to invited educators and participants.
          </p>

          <section>
            <h2 className="text-title-md text-text-main">Pilot use</h2>
            <p className="mt-3">
              The platform is provided for educational and research purposes. Generated 3D models
              are aids for teaching and learning — not clinical diagnosis, treatment planning, or
              medical devices. Do not use outputs for direct patient care decisions.
            </p>
          </section>

          <section>
            <h2 className="text-title-md text-text-main">Accounts and invites</h2>
            <p className="mt-3">
              You are responsible for your account credentials. Invite links and access codes are
              for authorised participants only; do not share them publicly outside your cohort.
            </p>
          </section>

          <section>
            <h2 className="text-title-md text-text-main">Content you upload</h2>
            <p className="mt-3">
              You must have rights to images you upload. Do not upload patient-identifiable
              clinical records unless permitted under your institution&apos;s ethics approval and
              data handling procedures.
            </p>
          </section>

          <section>
            <h2 className="text-title-md text-text-main">Availability</h2>
            <p className="mt-3">
              As a research pilot, the service may change, pause, or limit features (including GPU
              generation) without notice. We aim for reasonable uptime but do not guarantee
              uninterrupted access.
            </p>
          </section>

          <section>
            <h2 className="text-title-md text-text-main">Research participation</h2>
            <p className="mt-3">
              Separate consent applies to research data collection. See the in-app consent flow
              and participant information sheet before contributing research data.
            </p>
          </section>
        </div>

        <p className="mt-10 text-body-sm">
          <Link href="/" className="text-primary-container hover:underline">
            ← Back to {APP_NAME}
          </Link>
          {" · "}
          <Link href="/privacy" className="text-primary-container hover:underline">
            Privacy Policy
          </Link>
        </p>
      </main>
    </div>
  );
}
