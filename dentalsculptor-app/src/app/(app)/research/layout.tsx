import { redirect } from "next/navigation";
import { getAuthUser, isResearcherOrAdmin } from "@/lib/auth";

export default async function ResearchLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const user = await getAuthUser();
  if (!user) redirect("/sign-in");
  if (!isResearcherOrAdmin(user.role)) redirect("/dashboard");

  return children;
}
