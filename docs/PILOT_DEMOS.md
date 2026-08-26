# Pilot launch — interactive demos

**Goal:** Recruit educators/students to test DentalSculptor with guided, repeatable flows.

## Demo 1 — Landing → 3D → Editor (5 min)

1. Open `/` (or production URL)
2. **Select image** or **Browse library**
3. **Generate 3D model** → wait for preview
4. Sign in if prompted → **Open in editor**
5. Rename project in header (click title, type, Enter)

**Success:** Model visible in editor after refresh.

## Demo 2 — Dashboard new project (5 min)

1. Dashboard → **New Project**
2. Same image picker (Select / Browse library / Clear / Rotate)
3. Generate → **Open Editor**
4. Confirm title auto-named from filename

**Success:** Same UX as landing; model persisted in DB.

## Demo 3 — Teaching case + edit presets (10 min)

1. In editor with a generated molar/incisor
2. Case wizard → pick **Pathology** or **Cusp fracture** case
3. On ISO chart: tap tooth number (e.g. FDI 16) → tooth type auto-fills
4. Apply template → title becomes `Case name · FDI 16 · Molar · date`
5. **Edit presets** panel opens (case-specific suggestions)
6. **Mask tool** → paint region → pick preset → instruction fills
7. **Preview 2D** → progress bar → approve → **Generate 3D**

**Success:** Send ↑ activates when mask + instruction ready; 2D preview shows visible change in masked area.

## Demo 4 — Export (3 min)

1. With model + optional case applied
2. Export wizard → Simodont / Quest / teaching ZIP
3. Download bundle

## What to tell testers

- FDI tooth number is **manual** (ISO chart) — we do not auto-detect from photos yet
- 2D preview uses AI inpaint when `MODAL_INPAINT_URL` or `FAL_KEY` is set; otherwise local clinical stub
- 3D edit is Nano3D CPU v1 today (masked vertex deform); GPU FlowEdit is E3
- Report unwanted **caries-like** generation on sound teeth — useful for E3 finetuning

## Metrics to collect

- Time upload → first 3D
- Case wizard completion rate
- Edit: mask → preview → accept/reject
- Export format chosen

See `research/` events and `/research` dashboard when signed in as researcher.
