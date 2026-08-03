# DentalSculptor — Architecture Document

## System Purpose

DentalSculptor is a production MVP for:
- Educational deployment and user testing
- Pilot studies and doctoral research data collection
- Future commercialisation as a dental learning SaaS

## Core Principles

1. **AI Co-Creation, Not Replacement** — Educators remain creators; AI assists
2. **Research by Design** — Every important interaction generates research data
3. **Clinical Precision UI** — Professional, academic, medical-grade aesthetic

## Database Schema

### Core Entities

| Model | Purpose |
|-------|---------|
| User | Clerk-synced users with role, institution, consent |
| Project | Learning experience container |
| DentalModel | 3D mesh data, source images |
| Annotation | 3D surface markers with educational text |
| LearningObjective | Pedagogical goals |
| Assessment | Quiz/assessment questions |
| CommunityProject | Published community metadata (likes, downloads) |
| StudentAssignment | Student-project assignments |
| ResearchEvent | All tracked interactions |
| SurveyResponse | Likert scale survey data |

### Enums

- `UserRole`: EDUCATOR, STUDENT, RESEARCHER, ADMINISTRATOR
- `ProjectStatus`: DRAFT, PROCESSING, READY, PUBLISHED, ARCHIVED
- `PublishingLevel`: PRIVATE, CLASSROOM, INSTITUTION, COMMUNITY, PUBLIC
- `ResearchEventType`: 25+ event types for comprehensive tracking

## Authentication Flow

```
Landing → Sign Up/In (Clerk) → Consent → Onboarding → Dashboard
```

Clerk handles OAuth (Google, Microsoft) and email magic links. User records sync to PostgreSQL on first authenticated request.

## Research Instrument

### Metrics Computed

- **Ownership Score** — Annotations, publishing, AI rejection rate
- **Agency Score** — Authoring actions per session
- **Personalisation Score** — Model generation + annotation density
- **Confidence Score** — Publishing frequency + AI acceptance

### Survey Engine

Built-in Likert scale (1–5) with 5 standard questions about control, personalisation, teaching goals, AI workflow, and adoption intent.

## 3D Editor Architecture

```
┌──────────────┬─────────────────────────┬──────────────────┐
│  Left Panel  │     Three.js Canvas     │  Right Panel     │
│  Annotations │     (R3F + Drei)        │  Properties      │
│  AI Assistant│     OrbitControls       │  Educational     │
│  Objectives  │     Annotation markers    │  Export          │
└──────────────┴─────────────────────────┴──────────────────┘
```

Click-to-annotate saves 3D coordinates + text to database with research event logging.

## API Design

RESTful API routes under `/api/`:

- Resource-oriented (`/api/projects/[id]/annotations`)
- Auth via Clerk session on every request
- Research events tracked server-side for data integrity

## Deployment Architecture

```
Users → Vercel Edge → Next.js Server → Supabase PostgreSQL
                    → AWS S3 (assets)
                    → Clerk (auth)
                    → PostHog (analytics)
Meta Quest → WebXR → Same Vercel deployment
```

## Future Extensions

- DICOM/STL/OBJ file import
- Real AI reconstruction pipeline integration
- Unity package export
- Institution SSO (SAML)
- Real-time collaboration
