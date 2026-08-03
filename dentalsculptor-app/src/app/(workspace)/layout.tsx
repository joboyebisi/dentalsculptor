import { redirect } from "next/navigation";
import { getAuthUser } from "@/lib/auth";

export const dynamic = "force-dynamic";

export default async function WorkspaceLayout({
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

  return <>{children}</>;
}
