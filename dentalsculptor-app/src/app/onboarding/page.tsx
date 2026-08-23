"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  GraduationCap,
  BookOpen,
  BarChart3,
  Shield,
  Plus,
  Users,
  Play,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { ONBOARDING_ROLES } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { getPendingLandingProject } from "@/lib/landing-session";
import { useAuthGate } from "@/hooks/use-auth-gate";

const roleIcons = {
  EDUCATOR: GraduationCap,
  STUDENT: BookOpen,
  RESEARCHER: BarChart3,
  ADMINISTRATOR: Shield,
};

export default function OnboardingPage() {
  const router = useRouter();
  const { checking } = useAuthGate("onboarding");
  const [step, setStep] = useState(1);
  const [role, setRole] = useState("");
  const [institution, setInstitution] = useState("");
  const [department, setDepartment] = useState("");
  const [country, setCountry] = useState("");
  const [loading, setLoading] = useState(false);

  async function completeOnboarding() {
    setLoading(true);
    try {
      const res = await fetch("/api/user/onboarding", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role, institution, department, country }),
      });
      if (!res.ok) {
        const data = (await res.json().catch(() => null)) as { error?: string } | null;
        throw new Error(data?.error ?? "Could not save onboarding details");
      }

      if (getPendingLandingProject()) {
        router.push("/auth/continue");
        return;
      }

      setStep(3);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      {checking ? (
        <p className="text-body-md text-on-surface-variant">Loading…</p>
      ) : (
      <div className="w-full max-w-lg">
        <div className="mb-8 flex justify-center gap-2">
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              className={cn(
                "h-1.5 w-16 rounded-full transition-colors",
                s <= step ? "bg-primary-container" : "bg-surface-container"
              )}
            />
          ))}
        </div>

        <AnimatePresence mode="wait">
          {step === 1 && (
            <motion.div
              key="step1"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
            >
              <h1 className="mb-2 text-center text-display-lg">Select Your Role</h1>
              <p className="mb-8 text-center text-body-md text-on-surface-variant">
                This helps us personalise your experience
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                {ONBOARDING_ROLES.map((r) => {
                  const Icon = roleIcons[r.value as keyof typeof roleIcons];
                  return (
                    <button
                      key={r.value}
                      onClick={() => setRole(r.value)}
                      className={cn(
                        "rounded-xl border p-4 text-left transition-all hover:border-primary-container",
                        role === r.value
                          ? "border-primary-container bg-primary-container/5"
                          : "border-border-subtle bg-panel-bg"
                      )}
                    >
                      <Icon className="mb-2 h-6 w-6 text-primary-container" />
                      <p className="font-semibold">{r.label}</p>
                      <p className="mt-1 text-body-sm text-on-surface-variant">
                        {r.description}
                      </p>
                    </button>
                  );
                })}
              </div>
              <Button
                className="mt-8 w-full"
                disabled={!role}
                onClick={() => setStep(2)}
              >
                Continue
              </Button>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div
              key="step2"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
            >
              <h1 className="mb-2 text-center text-display-lg">Institution Details</h1>
              <p className="mb-8 text-center text-body-md text-on-surface-variant">
                Tell us about your academic affiliation
              </p>
              <div className="space-y-4">
                <div>
                  <Label htmlFor="institution">Institution</Label>
                  <Input
                    id="institution"
                    value={institution}
                    onChange={(e) => setInstitution(e.target.value)}
                    placeholder="University or organisation"
                    className="mt-1.5"
                  />
                </div>
                <div>
                  <Label htmlFor="department">Department</Label>
                  <Input
                    id="department"
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    placeholder="e.g. Restorative Dentistry"
                    className="mt-1.5"
                  />
                </div>
                <div>
                  <Label htmlFor="country">Country</Label>
                  <Input
                    id="country"
                    value={country}
                    onChange={(e) => setCountry(e.target.value)}
                    placeholder="United Kingdom"
                    className="mt-1.5"
                  />
                </div>
              </div>
              <div className="mt-8 flex gap-3">
                <Button variant="outline" onClick={() => setStep(1)}>
                  Back
                </Button>
                <Button
                  className="flex-1"
                  disabled={!institution || loading}
                  onClick={completeOnboarding}
                >
                  {loading ? "Saving..." : "Complete Setup"}
                </Button>
              </div>
            </motion.div>
          )}

          {step === 3 && (
            <motion.div
              key="step3"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
            >
              <div className="text-center">
                <h1 className="text-display-lg">Welcome to DentalSculptor</h1>
                <p className="mt-2 text-body-md text-on-surface-variant">
                  You&apos;re all set. What would you like to do first?
                </p>
              </div>
              <div className="mt-8 space-y-3">
                <Card
                  className="cursor-pointer transition-shadow hover:workbench-shadow"
                  onClick={() => router.push("/projects/new")}
                >
                  <CardContent className="flex items-center gap-4 p-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-container/10">
                      <Plus className="h-5 w-5 text-primary-container" />
                    </div>
                    <div>
                      <p className="font-semibold">Create New Project</p>
                      <p className="text-body-sm text-on-surface-variant">
                        Upload an image and generate a 3D model
                      </p>
                    </div>
                  </CardContent>
                </Card>
                <Card
                  className="cursor-pointer transition-shadow hover:workbench-shadow"
                  onClick={() => router.push("/community")}
                >
                  <CardContent className="flex items-center gap-4 p-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-research-indigo/10">
                      <Users className="h-5 w-5 text-research-indigo" />
                    </div>
                    <div>
                      <p className="font-semibold">Explore Community</p>
                      <p className="text-body-sm text-on-surface-variant">
                        Discover and clone learning experiences
                      </p>
                    </div>
                  </CardContent>
                </Card>
                <Card className="opacity-70">
                  <CardContent className="flex items-center gap-4 p-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary/10">
                      <Play className="h-5 w-5 text-secondary" />
                    </div>
                    <div>
                      <p className="font-semibold">Watch Tutorial</p>
                      <p className="text-body-sm text-on-surface-variant">
                        Coming soon — guided walkthrough for educators and students
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      )}
    </div>
  );
}
