"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, CheckCircle2 } from "lucide-react";
import { AppLogo } from "@/components/brand/app-logo";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RESEARCH_INFO_SHEET_URL } from "@/lib/constants";

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

          <div className="space-y-4 rounded-xl border border-border-subtle bg-surface-container-low p-4">
            <div className="flex items-start gap-3">
              <Checkbox
                id="consent"
                checked={consent}
                onCheckedChange={(v) => setConsent(v === true)}
              />
              <Label htmlFor="consent" className="cursor-pointer leading-relaxed">
                I consent to anonymised interaction data being collected and analysed.{" "}
                <span className="text-error">*</span>
              </Label>
            </div>
            <div className="flex items-start gap-3">
              <Checkbox
                id="research-opt-in"
                checked={researchOptIn}
                onCheckedChange={(v) => setResearchOptIn(v === true)}
              />
              <Label htmlFor="research-opt-in" className="cursor-pointer leading-relaxed">
                I agree to be contacted regarding future research studies. (Optional)
              </Label>
            </div>
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
