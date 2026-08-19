import { redirect } from "next/navigation";
import { getAuthUser } from "@/lib/auth";

export const dynamic = "force-dynamic";

export default async function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const user = await getAuthUser();

  if (!user) {
    redirect("/sign-in");
  }

  if (!user.consentAccepted) {
    redirect("/consent");
  }

  if (!user.onboardingCompleted) {
    redirect("/onboarding");
  }

  return <>{children}</>;
}
