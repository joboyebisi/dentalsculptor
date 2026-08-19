# Stitch mockup prompts — Milestone E0–E2 screens

Copy each prompt into Stitch. Reference design system: `stitch_dentalsculptor_xr_authoring_platform/clinical_precision_1/DESIGN.md` (Inter + JetBrains Mono, clinical navy/teal, cream viewport `#F3F4F6`).

---

## 1. Case wizard (New project step 2)

```
Design a "Clinical case wizard" screen for DentalSculptor, a web app for dental educators authoring 3D teaching cases.

Context: User already uploaded a single-tooth PNG/JPG. This step lets them pick a training case template and student year level before AI generates a 3D model.

Layout:
- Top: progress stepper (Upload ✓ → Case → Generate → Edit → Export)
- Left panel (320px): filters — Student year (Year 1–5 chips), Procedure type (Anatomy, Caries, Operative, Crown, Endo, Pathology)
- Main area: responsive card grid (2–3 columns). Each card shows: case title, short description, difficulty badge (Intro / Intermediate / Advanced), year tags, recommended export target pill (Simodont / VR / Download)
- One card highlighted as "Recommended for your image"
- Bottom bar: "Skip — custom case" ghost button + primary "Continue to generate"

Style: Clean clinical SaaS, not consumer. White panels, subtle borders, teal primary (#0F766E), navy headings (#0F172A). Accessible contrast. No stock dental photos — use abstract tooth icons.

Include empty state: "No templates match filters — clear filters or create custom case."

Mobile: stack filters in accordion above cards.
```

---

## 2. Export wizard

```
Design an "Export wizard" modal/page for DentalSculptor. Educator exports a finished 3D tooth (optionally merged onto jaw) for simulators or VR.

Step 1 — Choose destination (card select, single choice):
- Simodont (haptic trainer) — STL/PLY, mm, watertight
- SimtoCARE Dente — STL/PLY, drillable import
- Virteasy Dental — STL for exercises / 3D print
- Meta Quest — GLB for VR display
- Teaching bundle — ZIP with GLB + STL + README

Each card: platform logo placeholder, 1-line requirement, warning badge if "geometry only — uniform haptic hardness" applies.

Step 2 — Validation panel:
- Checklist with icons: Watertight mesh ✓, Manifold ✓, Units mm ✓, Triangle count 124k (under limit) ✓
- Amber callout for Simodont: "Custom STL imports use uniform drill resistance. For soft caries feel, use Simodont native cariology library or TrueTeethLab (CBCT) — link Learn more."

Step 3 — Download:
- Filename preview: occlusal-caries-year3-simodont.stl
- Primary "Download" + secondary "Send to classroom assignment"
- Success toast with checkmark

Style: Same DentalSculptor design system. Modal width 640px on desktop. Step indicator at top.
```

---

## 3. Placement Studio

```
Design "Placement Studio" — a split-view authoring screen in DentalSculptor for placing a generated single tooth onto a jaw template before export.

Layout:
- Header: "Placement Studio" + FDI tooth selector dropdown (e.g. 36) + "Reset transform"
- Left 60%: 3D viewport (cream background) showing lower jaw template mesh (grey gingiva) + highlighted tooth socket + user tooth mesh (white enamel tint). Transform gizmo on tooth (translate/rotate/scale tabs).
- Right 40% panel:
  - Jaw template library (thumbnail list: Adult lower, Adult upper, Quadrant — radio select)
  - Socket snap toggle "Snap to FDI socket"
  - Numeric transform readouts (mm, degrees) in JetBrains Mono
  - "Merge for export" checkbox
  - Tips: "Align occlusal plane parallel to jaw arch"
- Footer: Cancel | "Save placement" | "Continue to export"

Interaction hints: dashed circle at socket, subtle pulse on snap when aligned.

Style: Clinical precision, light mode editor chrome. Reference Meshmixer-style clarity but simpler for educators.
```

---

## 4. Edit mode — mask paint + 2D preview (bonus)

```
Design "Local edit" mode overlay for DentalSculptor 3D editor.

Top: captured camera view label "Editing view — occlusal"

Center: full-width 3D viewport with semi-transparent mask paint layer (red brush strokes on tooth surface). Left floating toolbar: Brush size slider, Erase, Undo, Clear mask.

Bottom dock:
- Operation segmented control: Add | Remove | Replace
- Text instruction field placeholder: "remove decay from central fossa"
- Buttons: "Preview 2D change" (secondary) | "Generate 3D edit" (primary, disabled until preview approved)

Modal "Approve 2D preview": side-by-side Before | After inpaint images, warning "Edits outside mask will be rejected", Approve / Retry.

Style: DentalSculptor editor — light viewport, dark minimal toolbar. Show revision badge "v2 pending".
```

---

## 5. Single-tooth upload (landing refinement)

```
Refine the DentalSculptor landing upload card for beta single-tooth scope.

Card title: "Upload dental image"
Subtitle: PNG or JPG of one tooth only

Amber info banner (icon + text): "Single tooth only (beta). Whole jaw and oral cavity workflows coming later. Best results: plain background, tooth fills frame."

Upload zone 4:3 aspect, dashed border. Below: accepted formats PNG, JPG — max 8MB.

Primary CTA: "Generate 3D model" full width.

Keep existing notify-me checkbox area. Clinical SaaS aesthetic matching clinical_precision design tokens.
```
