import Link from "next/link";
import { PublicFooter, PublicNav } from "@/components/layout/public-nav";
import { WebMcpDiagnostics } from "@/components/webmcp/webmcp-diagnostics";

export const metadata = {
  title: "WebMCP Judge Guide | DentalSculptor",
  description: "Inspect DentalSculptor's live WebMCP tools and human-agent dental authoring workflow.",
};

export default function WebMcpPage() {
  return (
    <div className="min-h-screen bg-background">
      <PublicNav />
      <main className="mx-auto max-w-4xl px-margin-page py-12 md:py-16">
        <p className="text-label-caps text-primary-container">WebMCP Challenge</p>
        <h1 className="mt-3 text-display-lg text-text-main">
          The agent coordinates. The educator owns the anatomy.
        </h1>
        <p className="mt-5 max-w-3xl text-body-md leading-relaxed text-on-surface-variant">
          DentalSculptor exposes structured, page-scoped tools for turning a tooth image into a
          visible 3D teaching case. The agent can inspect state, start generation, synchronize a
          clinical workflow, and prepare export or sharing. The educator keeps control of spatial
          marking, preview approval, revision acceptance, privacy, and public release.
        </p>

        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          {[
            ["Structured", "Agents receive explicit state, schemas, and valid next actions."],
            ["Visible", "Every action updates the same 3D workspace the educator is watching."],
            ["Reversible", "Clinical edits remain reviewable and rejectable before release."],
          ].map(([title, text]) => (
            <article key={title} className="rounded-xl border border-border-subtle bg-panel-bg p-5">
              <h2 className="font-semibold text-text-main">{title}</h2>
              <p className="mt-2 text-body-sm leading-relaxed text-on-surface-variant">{text}</p>
            </article>
          ))}
        </div>

        <div className="mt-8">
          <WebMcpDiagnostics />
        </div>

        <section className="mt-8 rounded-xl bg-surface-container-low p-6">
          <h2 className="text-headline-md font-semibold text-text-main">Try the collaboration</h2>
          <ol className="mt-4 list-decimal space-y-2 pl-5 text-body-sm text-on-surface-variant">
            <li>Open the production app in ChatGPT&apos;s in-app browser.</li>
            <li>Ask: “Inspect DentalSculptor and tell me what we can do together.”</li>
            <li>Select a curated tooth image, then ask the agent to generate the 3D model.</li>
            <li>Continue into a teaching case and keep the final anatomical decisions visible.</li>
          </ol>
          <Link
            href="/#workbench"
            className="mt-5 inline-flex rounded-lg bg-primary-container px-4 py-2 text-sm font-medium text-on-primary"
          >
            Open the 3D workbench
          </Link>
        </section>
      </main>
      <PublicFooter />
    </div>
  );
}
