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
  { href: "/research", label: "Research", icon: "BarChart3" },
  { href: "/settings", label: "Settings", icon: "Settings" },
] as const;

export const RESEARCH_INFO_SHEET_URL = "/research-information-sheet.pdf";
