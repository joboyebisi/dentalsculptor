"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, CheckCircle2 } from "lucide-react";
import { AppLogo } from "@/components/brand/app-logo";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RESEARCH_INFO_SHEET_URL } from "@/lib/constants";
import { cn } from "@/lib/utils";

const collectedData = [
  "Editing behaviour",
  "Authoring actions",
  "AI interactions",
  "Learning design choices",
  "Platform usage",
  "Survey responses",
];

export default function ConsentPage() {
  const router = useRouter();
  const [consent, setConsent] = useState(false);
  const [researchOptIn, setResearchOptIn] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleAccept() {
    if (!consent) return;
    setLoading(true);
    try {
      await fetch("/api/user/consent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ consentAccepted: true, researchContactOptIn: researchOptIn }),
      });
      router.push("/onboarding");
    } catch {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-xl">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex justify-center">
            <AppLogo size="md" href={null} showWordmark={false} />
          </div>
          <CardTitle className="text-display-lg">
            Research Participation and Platform Analytics
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <p className="text-body-md text-on-surface-variant">
            DentalSculptor is part of an ongoing research programme investigating educator
            interaction with AI-aided authoring tools. To improve the platform and support
            future educational research, anonymous and consented interaction data may be
            collected while you use the system.
          </p>

          <div>
            <h3 className="mb-3 text-label-caps text-on-surface-variant">Collected Data</h3>
            <ul className="space-y-2">
              {collectedData.map((item) => (
                <li key={item} className="flex items-center gap-2 text-body-sm">
                  <CheckCircle2 className="h-4 w-4 text-secondary" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="space-y-3 rounded-xl border border-outline-variant bg-surface-container p-4">
            <label
              htmlFor="consent"
              className={cn(
                "flex cursor-pointer items-start gap-3 rounded-lg border p-3.5 transition-colors",
                consent
                  ? "border-primary-container/40 bg-background shadow-sm"
                  : "border-border-subtle bg-background hover:border-outline-variant"
              )}
            >
              <Checkbox
                id="consent"
                checked={consent}
                onCheckedChange={(v) => setConsent(v === true)}
                className="mt-0.5 h-5 w-5 shrink-0 border-2 border-on-surface-variant/50 bg-background data-[state=checked]:border-primary-container data-[state=checked]:bg-primary-container"
              />
              <span className="cursor-pointer text-body-sm leading-relaxed text-on-surface">
                I consent to anonymised interaction data being collected and analysed.{" "}
                <span className="text-error">*</span>
              </span>
            </label>

            <label
              htmlFor="research-opt-in"
              className={cn(
                "flex cursor-pointer items-start gap-3 rounded-lg border p-3.5 transition-colors",
                researchOptIn
                  ? "border-secondary/40 bg-background shadow-sm"
                  : "border-border-subtle bg-background hover:border-outline-variant"
              )}
            >
              <Checkbox
                id="research-opt-in"
                checked={researchOptIn}
                onCheckedChange={(v) => setResearchOptIn(v === true)}
                className="mt-0.5 h-5 w-5 shrink-0 border-2 border-on-surface-variant/50 bg-background data-[state=checked]:border-secondary data-[state=checked]:bg-secondary"
              />
              <span className="cursor-pointer text-body-sm leading-relaxed text-on-surface">
                I agree to be contacted regarding future research studies. (Optional)
              </span>
            </label>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            <Button
              className="flex-1"
              disabled={!consent || loading}
              onClick={handleAccept}
            >
              Accept and Continue
            </Button>
            <Button variant="outline" className="flex-1" asChild>
              <a href={RESEARCH_INFO_SHEET_URL} target="_blank" rel="noopener noreferrer">
                <FileText className="mr-2 h-4 w-4" />
                View Research Information Sheet
              </a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
