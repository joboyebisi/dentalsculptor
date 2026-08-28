import { generateDentalMeshFromImage } from "@/lib/model-generator";

export const PREVIEW_MESH = generateDentalMeshFromImage(800, 600);

export const PREVIEW_EDITOR_PROJECT = {
  id: "preview-project-1",
  title: "Molar Caries Simulation",
  description: "Interactive restorative dentistry case study for preview",
  status: "READY",
  instructions: "Examine the occlusal surface and identify carious lesions.",
  hints: "Look for demineralisation patterns on the mesial marginal ridge.",
  feedback: "Well done — consider restoration options for Class II caries.",
  dentalModel: { meshData: PREVIEW_MESH },
  annotations: [
    { id: "a1", text: "Occlusal caries", position: [0.12, 0.45, -0.08], color: "#0F3D91", type: "point" },
    { id: "a2", text: "Marginal ridge", position: [-0.15, 0.42, 0.11], color: "#7C3AED", type: "point" },
  ],
  learningObjectives: [
    { id: "lo1", title: "Identify carious lesions", description: null },
    { id: "lo2", title: "Plan restorative treatment", description: null },
  ],
  assessments: [
    { id: "as1", question: "What type of restoration is indicated?", answer: null },
  ],
};

export const PREVIEW_PROJECTS = [
  {
    id: "preview-project-1",
    title: "Molar Caries Simulation",
    description: "Interactive restorative dentistry case study",
    status: "READY" as const,
    updatedAt: new Date(),
    thumbnailUrl: "/generation-library/upper-molar-three-roots-a.png",
    dentalModel: {
      sourceImageUrl: "/generation-library/upper-molar-three-roots-a.png",
      thumbnailUrl: "/generation-library/upper-molar-three-roots-a.png",
      meshData: null,
    },
    communityProject: null,
    _count: { annotations: 4, learningObjectives: 2 },
  },
  {
    id: "preview-project-2",
    title: "Root Canal Anatomy Explorer",
    description: "Endodontic anatomy for advanced students",
    status: "PUBLISHED" as const,
    updatedAt: new Date(Date.now() - 86400000),
    thumbnailUrl: "/generation-library/upper-canine-labial-a.png",
    dentalModel: {
      sourceImageUrl: "/generation-library/upper-canine-labial-a.png",
      thumbnailUrl: "/generation-library/upper-canine-labial-a.png",
      meshData: null,
    },
    communityProject: { published: true },
    _count: { annotations: 8, learningObjectives: 3 },
  },
];

export const PREVIEW_COMMUNITY = [
  {
    id: "preview-cp-1",
    likes: 42,
    downloads: 318,
    featured: true,
    rating: 4.7,
    project: {
      id: "preview-project-2",
      title: "Root Canal Anatomy Explorer",
      category: "Endodontics",
      thumbnailUrl: "/generation-library/upper-canine-labial-a.png",
      dentalModel: { sourceImageUrl: "/generation-library/upper-canine-labial-a.png", thumbnailUrl: "/generation-library/upper-canine-labial-a.png" },
      owner: { name: "Dr. Sarah Chen", institution: "King's College London" },
      learningObjectives: [{ id: "1", title: "Identify pulp chamber" }],
    },
  },
];

export const PREVIEW_METRICS = {
  totalEvents: 128,
  projectsCreated: 5,
  modelsGenerated: 4,
  aiAccepted: 12,
  aiRejected: 3,
  aiAcceptRate: 80,
  annotations: 24,
  published: 2,
  ownershipScore: 78,
  agencyScore: 85,
  personalisationScore: 72,
  confidenceScore: 81,
};

export const PREVIEW_EVENTS = [
  {
    id: "e1",
    eventType: "ANNOTATION_CREATED",
    timestamp: new Date(),
    project: { title: "Molar Caries Simulation" },
  },
  {
    id: "e2",
    eventType: "AI_SUGGESTION_ACCEPTED",
    timestamp: new Date(Date.now() - 3600000),
    project: { title: "Molar Caries Simulation" },
  },
];
