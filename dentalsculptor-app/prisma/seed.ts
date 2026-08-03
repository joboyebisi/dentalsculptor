import { PrismaClient } from "../src/generated/prisma/client";
import { PrismaPg } from "@prisma/adapter-pg";

const adapter = new PrismaPg({ connectionString: process.env.DATABASE_URL! });
const prisma = new PrismaClient({ adapter });

async function main() {
  await prisma.platformMetrics.upsert({
    where: { id: "platform" },
    create: {
      id: "platform",
      projectsCreated: 2400,
      studentsReached: 18500,
      experiencesPublished: 890,
      communityContributions: 1200,
      researchStudiesSupported: 12,
    },
    update: {},
  });

  console.log("Seed completed.");
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
