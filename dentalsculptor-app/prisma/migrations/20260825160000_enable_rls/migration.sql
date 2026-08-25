-- Enable Row Level Security on all public tables (Supabase Security Advisor / splinter).
-- See prisma/sql/enable_rls.sql (same content) and docs/SUPABASE_SETUP.md § RLS.

ALTER TABLE "User" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "PlatformMetrics" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Project" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Annotation" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "LearningObjective" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Assessment" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "CommunityProject" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "StudentAssignment" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "ResearchEvent" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "SurveyResponse" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Comment" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Bookmark" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Like" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "ProjectVersion" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "DentalModel" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "GenerationJob" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "_prisma_migrations" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "User" FROM anon, authenticated;
REVOKE ALL ON TABLE "PlatformMetrics" FROM anon, authenticated;
REVOKE ALL ON TABLE "Project" FROM anon, authenticated;
REVOKE ALL ON TABLE "Annotation" FROM anon, authenticated;
REVOKE ALL ON TABLE "LearningObjective" FROM anon, authenticated;
REVOKE ALL ON TABLE "Assessment" FROM anon, authenticated;
REVOKE ALL ON TABLE "CommunityProject" FROM anon, authenticated;
REVOKE ALL ON TABLE "StudentAssignment" FROM anon, authenticated;
REVOKE ALL ON TABLE "ResearchEvent" FROM anon, authenticated;
REVOKE ALL ON TABLE "SurveyResponse" FROM anon, authenticated;
REVOKE ALL ON TABLE "Comment" FROM anon, authenticated;
REVOKE ALL ON TABLE "Bookmark" FROM anon, authenticated;
REVOKE ALL ON TABLE "Like" FROM anon, authenticated;
REVOKE ALL ON TABLE "ProjectVersion" FROM anon, authenticated;
REVOKE ALL ON TABLE "DentalModel" FROM anon, authenticated;
REVOKE ALL ON TABLE "GenerationJob" FROM anon, authenticated;
REVOKE ALL ON TABLE "_prisma_migrations" FROM anon, authenticated;
