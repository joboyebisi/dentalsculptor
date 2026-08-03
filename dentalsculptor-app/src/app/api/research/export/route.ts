import { NextRequest, NextResponse } from "next/server";
import { getAuthUser, isResearcherOrAdmin } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { trackResearchEvent } from "@/lib/research-events";

export async function GET(req: NextRequest) {
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  if (!isResearcherOrAdmin(user.role)) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  const format = req.nextUrl.searchParams.get("format") ?? "JSON";

  await trackResearchEvent({
    userId: user.id,
    eventType: "EXPORT_REQUESTED",
    metadata: { format },
  });

  const [events, surveys, users] = await Promise.all([
    prisma.researchEvent.findMany({
      include: {
        user: { select: { email: true, role: true, institution: true } },
        project: { select: { title: true } },
      },
      orderBy: { timestamp: "desc" },
    }),
    prisma.surveyResponse.findMany({
      include: { user: { select: { email: true, role: true } } },
    }),
    prisma.user.findMany({
      select: {
        id: true,
        email: true,
        role: true,
        institution: true,
        consentAccepted: true,
        createdAt: true,
      },
    }),
  ]);

  const exportData = {
    exportedAt: new Date().toISOString(),
    researchEvents: events,
    surveyResponses: surveys,
    participants: users,
  };

  if (format === "CSV") {
    const csvRows = [
      "id,userId,projectId,eventType,timestamp,metadata",
      ...events.map((e) =>
        [e.id, e.userId, e.projectId ?? "", e.eventType, e.timestamp.toISOString(), JSON.stringify(e.metadata)].join(",")
      ),
    ];
    return new NextResponse(csvRows.join("\n"), {
      headers: {
        "Content-Type": "text/csv",
        "Content-Disposition": "attachment; filename=dentalsculptor-research.csv",
      },
    });
  }

  if (format === "XLSX") {
    const tsv = [
      "Question\tAnswer\tScale\tUser\tDate",
      ...surveys.map((s) =>
        [s.question, s.answer, s.scale ?? "", s.user.email, s.createdAt.toISOString()].join("\t")
      ),
    ].join("\n");
    return new NextResponse(tsv, {
      headers: {
        "Content-Type": "application/vnd.ms-excel",
        "Content-Disposition": "attachment; filename=dentalsculptor-research.xlsx",
      },
    });
  }

  return NextResponse.json(exportData, {
    headers: {
      "Content-Disposition": "attachment; filename=dentalsculptor-research.json",
    },
  });
}
