export const APP_NAME = "DentalSculptor";
export const APP_TAGLINE = "AI-Aided 3D authoring for dental educators";

export const COLORS = {
  primary: "#0F3D91",
  secondary: "#14B8A6",
  ai: "#7C3AED",
  research: "#4F46E5",
  success: "#10B981",
  warning: "#F59E0B",
  error: "#EF4444",
  background: "#F8FAFC",
  card: "#FFFFFF",
  border: "#E2E8F0",
  textPrimary: "#0F172A",
  textSecondary: "#64748B",
} as const;

/** Light grey viewport — matches editor workspace surface. */
export const VIEWPORT_THEME = {
  /** Mid-tone studio backdrop — white teeth read clearly against this. */
  background: "#a8b2c0",
  meshDefault: "#e8dcc8",
  meshHighlight: "#f5e6d3",
  grid: "#6b7280",
  gridSection: "#4b5563",
  selectEmissive: "#0F3D91",
} as const;

/** Shared editor workspace surface (viewport + chrome). */
export const EDITOR_SURFACE = "#f3f4f6" as const;

/** Dark editor chrome — tools, panels, AI bar. */
export const CHROME_THEME = {
  surface: "#0a0a0a",
  panel: "#111827",
  panelBorder: "#1f2937",
  text: "#f3f4f6",
  textMuted: "#9ca3af",
} as const;

export const USER_ROLES = [
  { value: "EDUCATOR", label: "Educator", description: "Create and publish dental learning experiences" },
  { value: "STUDENT", label: "Student", description: "Access simulations and complete assignments" },
  { value: "RESEARCHER", label: "Researcher", description: "Collect and analyse research data" },
  { value: "ADMINISTRATOR", label: "Administrator", description: "Manage users and platform settings" },
] as const;

export const COMMUNITY_CATEGORIES = [
  "Dental Anatomy",
  "Restorative Dentistry",
  "Endodontics",
  "Orthodontics",
  "Assessment Design",
  "XR Learning",
] as const;

export const PUBLISHING_LEVELS = [
  { value: "PRIVATE", label: "Private", description: "Only you can access" },
  { value: "CLASSROOM", label: "Classroom", description: "Assigned students only" },
  { value: "INSTITUTION", label: "Institution", description: "Your institution" },
  { value: "COMMUNITY", label: "Community", description: "DentalSculptor community" },
  { value: "PUBLIC", label: "Public", description: "Open to everyone" },
] as const;

export const EXPORT_FORMATS = ["CSV", "JSON", "XLSX"] as const;

export const LIKERT_QUESTIONS = [
  "I felt in control of the content.",
  "I was able to personalise the learning experience.",
  "The platform supported my teaching goals.",
  "The AI improved my workflow.",
  "I would use this platform in my teaching practice.",
] as const;

export const AI_PROMPT_EXAMPLES = [
  "Highlight carious regions",
  "Generate instructor notes",
  "Label anatomical landmarks",
  "Create assessment prompts",
  "Add learning objectives",
] as const;

export const PROCESSING_STAGES = [
  "Analyzing image...",
  "Identifying anatomy...",
  "Generating 3D model...",
  "Preparing editor...",
] as const;

export const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: "LayoutDashboard" },
  { href: "/projects", label: "Projects", icon: "FolderOpen" },
  { href: "/community", label: "Community", icon: "Users" },
  { href: "/students", label: "Students", icon: "GraduationCap" },
  { href: "/research", label: "Research", icon: "BarChart3", researcherOnly: true },
  { href: "/settings", label: "Settings", icon: "Settings" },
] as const;

/** Nav items visible for a given role (hides supervisor tools from participants). */
export function getNavItemsForRole(role: string) {
  return NAV_ITEMS.filter(
    (item) => !("researcherOnly" in item && item.researcherOnly) || role === "RESEARCHER" || role === "ADMINISTRATOR"
  );
}

/** Roles users may self-select during onboarding (supervisor roles are assigned separately). */
export const ONBOARDING_ROLES = USER_ROLES.filter(
  (r) => r.value === "EDUCATOR" || r.value === "STUDENT"
);

export const RESEARCH_INFO_SHEET_URL = "/research-information-sheet.pdf";
