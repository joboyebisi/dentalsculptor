import { redirect } from "next/navigation";
import { getAuthUser } from "@/lib/auth";
import { AppShell } from "@/components/layout/app-sidebar";

export const dynamic = "force-dynamic";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const user = await getAuthUser();

  if (user && !user.consentAccepted) {
    redirect("/consent");
  }

  if (user && !user.onboardingCompleted) {
    redirect("/onboarding");
  }

  return <AppShell>{children}</AppShell>;
}
