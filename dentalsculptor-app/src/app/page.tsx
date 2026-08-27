"use client";

import Link from "next/link";
import { Suspense } from "react";
import { ImagePlus, Zap, Box, Library, GraduationCap, BookOpen } from "lucide-react";
import { PublicNav, PublicFooter } from "@/components/layout/public-nav";
import { Button } from "@/components/ui/button";
import { AppLogo } from "@/components/brand/app-logo";
import { LandingModelProvider } from "@/context/landing-model-context";
import { LandingWorkbench } from "@/components/landing/landing-workbench";

const steps = [
  {
    icon: ImagePlus,
    title: "Upload",
    description: "Add a clear photograph of a single tooth — well lit, minimal background.",
  },
  {
    icon: Zap,
    title: "Generate",
    description:
      "AI reconstructs a full 3D tooth model from your photo. First run may take a few minutes while compute starts.",
  },
  {
    icon: Box,
    title: "Author & export",
    description:
      "Download for your target platform or publish the generated model, with optional case authoring when an edit is needed.",
  },
];

const communitySpotlights = [
  {
    title: "Restorative case studies",
    category: "Restorative Dentistry",
    description:
      "Share occlusal caries simulations and crown-preparation scenarios that students can explore in 3D before bench practice.",
  },
  {
    title: "Endodontic anatomy explorers",
    category: "Endodontics",
    description:
      "Publish pulp chamber and canal anatomy models for pre-clinical revision, assessment design, and immersive lab briefings.",
  },
  {
    title: "Assessment-ready modules",
    category: "Assessment Design",
    description:
      "Contribute annotated models with learning objectives and prompts that colleagues can adapt for their own cohorts.",
  },
];

export default function LandingPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-background">
          <PublicNav />
        </div>
      }
    >
      <LandingModelProvider>
        <LandingPageContent />
      </LandingModelProvider>
    </Suspense>
  );
}

function LandingPageContent() {
  return (
    <div className="min-h-screen bg-background">
        <PublicNav />

        {/* Hero */}
        <section className="border-b border-border-subtle bg-gradient-to-b from-surface-container-low to-background pt-14">
          <div className="mx-auto max-w-3xl px-margin-page py-16 text-center md:py-20">
            <div className="mb-6 flex justify-center">
              <AppLogo size="lg" href={null} showWordmark={false} />
            </div>
            <h1 className="text-display-lg text-text-main md:text-[2.25rem] md:leading-[2.75rem]">
              DentalSculptor
            </h1>
            <p className="mt-3 text-headline-md font-medium text-primary-container">
              AI-Aided 3D authoring for dental educators
            </p>
            <p className="mx-auto mt-4 max-w-2xl text-body-md text-on-surface-variant md:text-base">
              Upload dental images and generate editable 3D models for teaching,
              assessment, and immersive learning.
            </p>
          </div>
        </section>

        {/* Interactive workbench */}
        <section id="workbench" className="border-b border-border-subtle py-10 md:py-12 lg:py-8">
          <div className="mx-auto max-w-6xl px-margin-page">
            <div className="mb-6 text-center lg:mb-4">
              <h2 className="text-headline-md font-semibold text-text-main md:text-display-lg">
                Create a model
              </h2>
              <p className="mx-auto mt-1 max-w-xl text-body-md text-on-surface-variant">
                Upload an image and view the 3D reconstruction below.
              </p>
            </div>

            <LandingWorkbench />
          </div>
        </section>

        {/* How it works — below workbench */}
        <section id="how-it-works" className="border-b border-border-subtle bg-panel-bg py-16">
          <div className="mx-auto max-w-5xl px-margin-page">
            <h2 className="text-center text-headline-md font-semibold text-text-main md:text-display-lg">
              How it works
            </h2>
            <p className="mx-auto mt-3 max-w-2xl text-center text-body-md text-on-surface-variant">
              Upload a photo, generate a 3D model, then download or publish it. Editing is optional.
            </p>
            <div className="mt-10 grid gap-6 sm:grid-cols-3">
              {steps.map((step, i) => (
                <div
                  key={step.title}
                  className="flex flex-col items-center rounded-xl border border-border-subtle bg-background p-6 text-center"
                >
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary-container/10">
                    <step.icon className="h-6 w-6 text-primary-container" strokeWidth={1.5} />
                  </div>
                  <p className="text-label-caps text-primary-container">Step {i + 1}</p>
                  <h3 className="mt-2 font-semibold text-text-main">{step.title}</h3>
                  <p className="mt-2 text-body-sm leading-relaxed text-on-surface-variant">
                    {step.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Community project spotlights */}
        <section id="community" className="border-b border-border-subtle py-16 md:py-20">
          <div className="mx-auto max-w-5xl px-margin-page">
            <div className="text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-secondary/10">
                <Library className="h-6 w-6 text-secondary" />
              </div>
              <h2 className="text-headline-md font-semibold text-text-main md:text-display-lg">
                Community project spotlights
              </h2>
              <p className="mx-auto mt-3 max-w-2xl text-body-md text-on-surface-variant">
                Educators publish and adapt 3D learning experiences across restorative dentistry,
                endodontics, and assessment design — building a shared library for teaching teams.
              </p>
            </div>

            <div className="mt-10 grid gap-6 md:grid-cols-3">
              {communitySpotlights.map((spotlight) => (
                <article
                  key={spotlight.title}
                  className="flex flex-col rounded-xl border border-border-subtle bg-panel-bg p-6"
                >
                  <span className="text-label-caps text-secondary">{spotlight.category}</span>
                  <h3 className="mt-2 font-semibold text-text-main">{spotlight.title}</h3>
                  <p className="mt-2 flex-1 text-body-sm leading-relaxed text-on-surface-variant">
                    {spotlight.description}
                  </p>
                </article>
              ))}
            </div>

            <div className="mt-10 text-center">
              <Link href="/community">
                <Button variant="outline">Browse community projects</Button>
              </Link>
            </div>
          </div>
        </section>

        {/* Research */}
        <section id="research" className="bg-surface-container-low py-16 md:py-20">
          <div className="mx-auto max-w-3xl px-margin-page text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary-container/10">
              <GraduationCap className="h-6 w-6 text-primary-container" />
            </div>
            <h2 className="text-headline-md font-semibold text-text-main md:text-display-lg">
              Research context
            </h2>
            <p className="mt-6 text-left text-body-md leading-relaxed text-on-surface-variant md:text-center">
              This 3D/VR content authoring tool being developed is part of ongoing research by{" "}
              <span className="font-medium text-on-surface">Job Oyebisi</span>,{" "}
              <span className="font-medium text-on-surface">Marie-Luce Bourguet</span>, and{" "}
              <span className="font-medium text-on-surface">Tony Stockman</span> at{" "}
              <span className="font-medium text-on-surface">Queen Mary University of London</span>.
              The research is funded by EPSRC as part of The Centre for Doctoral Training (CDT) in
              Data-Centric Engineering, and forms part of the UK Research and Innovation&apos;s
              (UKRI) Doctoral Mobility Pilot.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <a href="#how-it-works">
                <Button variant="outline" size="sm">
                  <BookOpen className="mr-2 h-4 w-4" />
                  How it works
                </Button>
              </a>
            </div>
          </div>
        </section>

        <PublicFooter />
      </div>
  );
}
