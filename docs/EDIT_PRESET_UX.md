# Edit preset UX — tooth-aware authoring workflow

**Updated:** 25 August 2026  
**Status:** Implemented (v1) — FDI gating, haptic disclosure, case-first flow

---

## Problem

The 12 edit presets are useful only when they match:

1. **Tooth morphology** (incisor vs molar cusp presets)
2. **Case template** (caries vs crown prep vs endo)
3. **Surface** (occlusal Class I vs buccal smooth-surface)
4. **Haptic tier** (visual caries texture ≠ soft drill feel on Simodont STL)

Without gating, an educator who generated an **incisor** could pick **“Remove cusp”** or a student could pick **FDI 36** in the case wizard while viewing an unrelated mesh — confusing and bad for research logs.

---

## Design principle: case before preset

```text
Create / open project
  → Case wizard: template + FDI tooth + surface + depth
  → Generate or load mesh (single tooth from photo)
  → Editor inherits case context (FDI, tooth type, surface)
  → Mask region aligned to surface hint
  → Presets filtered by tooth type; incompatible hidden
  → Preview 2D → Generate 3D → Accept revision
  → Export: pick assets simulator actually needs
```

**Rule:** FDI and tooth type come from the **case recipe**, not from the preset bar. Presets never override FDI — they append anatomical prompt text only.

---

## Tooth type resolution (priority order)

| Priority | Source | Example |
|----------|--------|---------|
| 1 | FDI digit in case recipe | FDI `36` → molar |
| 2 | Explicit `toothType` clinical field | anatomy template |
| 3 | Mesh bbox aspect (fallback) | wide crown → molar |
| 4 | Unknown | show warning; hide molar-only presets |

Implementation: `tooth-taxonomy.ts`, `edit-preset-context.ts`.

---

## Preset compatibility matrix

| Preset | Tooth types | Surface hint |
|--------|-------------|--------------|
| Remove / Add caries | all | any |
| Cusp fracture, Add/Remove/Replace cusp | premolar, molar | occlusal/buccal |
| Class I prep, Endo access | premolar, molar | occlusal |
| Incisal edge | incisor | incisal |
| Crown prep | all | any |
| Stain / Whiten | all | any (texture) |

Incompatible presets are **hidden** with expandable explanation — not disabled mid-click.

---

## Edit modes: geometry vs texture

| Mode | UI badge | Export haptics |
|------|----------|----------------|
| **geometry** | “shape” | STL changes drill path; still uniform hardness |
| **texture** | “look” | PLY/GLB may show stain/caries color; Simodont STL = uniform |
| **both** | (none) | Caries excavation — shape + dark texture |

Caries presets show **haptic notice** (amber callout):

> Visual lesion only — Simodont STL import drills with uniform hardness. Soft caries feel requires native Simodont cariology or TrueTeethLab (CBCT).

See [HAPTIC_EXPORT_STRATEGY.md](./HAPTIC_EXPORT_STRATEGY.md) Tier A/B/C.

---

## Recommended educator flow (molar caries example)

1. **New project** → template **“Caries — single tooth”**
2. Case wizard: **FDI 36**, surface **occlusal**, site **central fissure**, depth **outer dentin**
3. Upload molar photo → generate GLB
4. Editor opens with case panel showing FDI 36 · molar · occlusal
5. Paint mask on occlusal fissure (workflow panel guides steps)
6. Tap preset **Remove caries** → operation `remove`, prompt pre-filled, haptic notice visible
7. **Preview 2D** → approve → **Generate 3D** → **Accept revision**
8. Export → Simodont → check **Tooth mesh (STL)** only + optional README

---

## Incisor mismatch prevention

If case says FDI **11** (incisor) but photo looks like a molar:

- Presets **Add cusp**, **Class I**, **Endo access** are hidden
- **Incisal edge** preset highlighted
- Case panel shows FDI 11 · incisor — educator should fix case or re-upload photo

Future (E2): warn at generation if `prepare-generation-image` aspect ratio disagrees with FDI.

---

## Export asset selection

Simulators often need **one watertight STL** — not GLB, source photo, or jaw template.

Export wizard **Include in download**:

| Asset | Simodont default | Quest default |
|-------|------------------|---------------|
| Tooth mesh (primary) | ✓ STL | ✓ GLB |
| Source photo | ✗ | optional |
| Reference GLB | ✗ | ✓ |
| Jaw STL | optional (E2 placement) | optional |
| README (haptic tier) | optional | optional |

Implementation: `export-asset-options.ts`, `export-readme.ts`.

---

## 2D inpaint provider priority (cost)

| Priority | Provider | Cost |
|----------|----------|------|
| 1 | **Modal SDXL** (`MODAL_INPAINT_URL`) | Self-hosted — GPU seconds only |
| 2 | fal.ai SDXL inpaint (`FAL_KEY`) | ~$0.03–0.04 per 1024² preview |
| 3 | Client stub | Free, instant, low quality |

fal is **not free** for production volume. Prefer Modal + Hugging Face `diffusers/stable-diffusion-xl-1.0-inpainting-0.1`.

Deploy inpaint: redeploy Modal with GPU; set `MODAL_INPAINT_URL` in Vercel.

---

## Research events

| Event | Metadata |
|-------|----------|
| `AI_PROMPT_SUBMITTED` | `stage: 2d-inpaint`, `provider`, FDI, presetId |
| `EXPORT_REQUESTED` | `selectedAssets[]`, `hapticRealism` |

---

## Future UX (E2+)

- [ ] FDI ↔ mesh morphology validation at generate time
- [ ] Preset → auto camera view (occlusal for Class I)
- [ ] Protected-region metrics (3.9) tied to case anatomy roles
- [ ] ZIP bundle export with selected assets (4.5)
- [ ] Qwen-Image dental LoRA on Modal A100 when dataset ready
