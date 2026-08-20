/**
 * Enable UI-only local testing without Clerk or database.
 * Set UI_PREVIEW_MODE=true in .env
 */
export function isUiPreviewMode(): boolean {
  return process.env.UI_PREVIEW_MODE === "true";
}

export const PREVIEW_USER = {
  id: "preview-user",
  supabaseId: "preview-supabase",
  email: "educator.preview@university.ac.uk",
  name: "Dr. Preview Educator",
  role: "EDUCATOR" as const,
  institution: "Preview University",
  department: "Restorative Dentistry",
  country: "United Kingdom",
  consentAccepted: true,
  researchContactOptIn: false,
  onboardingCompleted: true,
  avatarUrl: null,
  createdAt: new Date(),
  updatedAt: new Date(),
};
