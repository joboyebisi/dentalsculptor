import type { Metadata } from "next";
import Link from "next/link";
import { AppLogo } from "@/components/brand/app-logo";
import { APP_NAME } from "@/lib/constants";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: `Privacy policy for ${APP_NAME} — research pilot platform for dental educators.`,
};

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border-subtle bg-panel-bg px-margin-page py-4">
        <AppLogo size="sm" href="/" />
      </header>
      <main className="mx-auto max-w-3xl px-margin-page py-10">
        <h1 className="text-display-md text-text-main">Privacy Policy</h1>
        <p className="mt-2 text-body-sm text-on-surface-variant">Last updated: August 2026</p>

        <div className="prose prose-slate mt-8 max-w-none space-y-6 text-body-md text-on-surface-variant">
          <p>
            {APP_NAME} is an AI-aided 3D authoring platform for dental educators, operated as
            part of an academic research programme. This policy describes how we handle personal
            data during the research pilot.
          </p>

          <section>
            <h2 className="text-title-md text-text-main">What we collect</h2>
            <ul className="mt-3 list-disc space-y-2 pl-5">
              <li>Account information (email, name) when you sign in via email or OAuth providers</li>
              <li>Platform usage data (projects, authoring actions, generation jobs) for service delivery</li>
              <li>Research analytics and survey responses when you provide consent</li>
              <li>Uploaded images and generated 3D assets stored to provide the service</li>
            </ul>
          </section>

          <section>
            <h2 className="text-title-md text-text-main">How we use data</h2>
            <p className="mt-3">
              Data is used to operate the platform, authenticate users, store teaching cases, and
              — where you have consented — to analyse educator interaction with AI-aided authoring
              tools for doctoral research. We do not sell personal data.
            </p>
          </section>

          <section>
            <h2 className="text-title-md text-text-main">Third-party services</h2>
            <p className="mt-3">
              We use Supabase (authentication and database), Vercel (hosting), Modal (GPU
              inference), and AWS S3 (asset storage). OAuth sign-in is processed by Google and
              Microsoft according to their respective policies.
            </p>
          </section>

          <section>
            <h2 className="text-title-md text-text-main">Retention and your rights</h2>
            <p className="mt-3">
              Research data is retained according to the approved research protocol. You may
              request access to or deletion of your account data by contacting the research team
              through your institution or the address provided in your invite materials.
            </p>
          </section>

          <section>
            <h2 className="text-title-md text-text-main">Contact</h2>
            <p className="mt-3">
              For privacy questions about this pilot, contact the DentalSculptor research team
              via the details in your participant information sheet.
            </p>
          </section>
        </div>

        <p className="mt-10 text-body-sm">
          <Link href="/" className="text-primary-container hover:underline">
            ← Back to {APP_NAME}
          </Link>
        </p>
      </main>
    </div>
  );
}
