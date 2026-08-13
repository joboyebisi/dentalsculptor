# DentalSculptor — Development Progress

Track completed work and what is next. Updated as sprints finish.

**Last updated:** 13 August 2026

---

## Phase A — Editor polish (Pascal-inspired)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| A1 | Design tokens (`VIEWPORT_THEME`, `CHROME_THEME`) | ✅ Done | `src/lib/constants.ts`, `globals.css` |
| A2a | 3D highlight on selection | ✅ Done | Emissive tint + outline ring in viewer |
| A2b | Part visibility ↔ mesh opacity | ✅ Done | Opacity scales with visible part count |
| A2c | Panel ↔ viewer active part sync | ✅ Done | Click part row to highlight |
| A2d | Mesh click selects model | ✅ Done | Existing + SFX |
| A3 | SFX bus (tool, select, toggle) | ✅ Done | `src/lib/sfx-bus.ts` (Web Audio) |
| A4 | Tools pane tooltips + SFX on change | ✅ Done | `editor-tool-palette.tsx` |
| A4b | Editor dark chrome styling | ✅ Done | `.editor-chrome` — near-black chrome, cream viewport |
| A5 | Undo/redo (Zundo) | ⏳ Phase B | Buttons present, not wired |
| A5 | Scene registry per-part meshes | ⏳ Phase E | Needs real segmentation |

**Phase A status: ~85% complete** (core polish done; undo/redo deferred)

---

## Auth & navigation

| Task | Status | Notes |
|------|--------|-------|
| Public nav Sign in / Register (right side) | ✅ Done | Hero duplicate CTAs removed — auth only in nav |
| ClerkProvider when keys present | ✅ Done | Sign-in works even in UI preview mode |
| Landing → editor auth flow | ✅ Done | Session in `sessionStorage`, `/auth/continue` |
| Role-gate `/research` nav | ⏳ Phase F | Still in default nav |

---

## Mesh generation

| Task | Status | Notes |
|------|--------|-------|
| fal.ai Hunyuan 3D v3.1 API route | ✅ Done | `/api/generate/mesh` |
| Landing workbench uses fal.ai | ✅ Done | `landing-model-context.tsx` → POST mesh route |
| Anonymous landing generation | ✅ Done | Auth optional on `/api/generate/mesh` |
| Editor Generate button wired | ✅ Done | Upload → POST → GLB in viewer |
| GLB loading in viewer | ✅ Done | `useGLTF` in `cam-model-viewer.tsx` + landing `dental-viewer.tsx` |
| Projects API uses fal.ai | ✅ Done | `POST /api/projects` — fal or reuse landing `modelUrl` |
| Persist mesh to Supabase storage | ⏳ Phase B | Source image uploaded; GLB URL stored as `generated3DUrl` |

---

## Landing → editor flow

| Step | Behaviour |
|------|-----------|
| Generate on landing | Real fal.ai via `/api/generate/mesh` (requires `FAL_KEY`) |
| Open in editor (signed out) | Draft saved → sign up → consent → onboarding → `/auth/continue` |
| Open in editor (returning user) | Draft saved → `/auth/continue` → project created → editor |
| Project naming | Auto from filename + date (`autoProjectTitle`); rename in editor header |
| Consent checkboxes | Higher contrast bordered rows — clinical navy/teal, not garish |

Key files: `src/lib/landing-session.ts`, `src/app/(workspace)/auth/continue/page.tsx`

---

## Documentation

| Doc | Status |
|-----|--------|
| PROJECT_WALKTHROUGH.md | ✅ |
| IMPLEMENTATION_PLAN.md | ✅ |
| DEPLOYMENT.md | ✅ |
| ENV.md | ✅ |
| PROGRESS.md | ✅ (this file) |

---

## Next up (Phase B)

1. STL export (real download)
2. Copy generated GLB from fal URL into Supabase Storage (durability)
3. Preview / share / publish routes
4. Undo/redo stack
5. Turn off preview mode for production pilot

---

## Quick test checklist

- [ ] Landing workbench → upload image → **Generate 3D model** (requires `FAL_KEY`)
- [ ] **Open in editor** while signed out → sign up → consent → onboarding → editor with model
- [ ] **Open in editor** as returning user → straight to editor with persisted model
- [ ] Rename project via click on title in editor header → Save
- [ ] New project from dashboard — no title step; auto-named from filename
- [ ] Consent page — checkbox rows clearly visible
- [ ] Toggle parts panel → mesh opacity changes
- [ ] Tool palette → hear subtle click sound
