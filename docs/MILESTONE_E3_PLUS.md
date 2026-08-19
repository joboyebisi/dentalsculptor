# Milestone E3+ — Segmentation, multi-input, full arch

**Status:** Planned (after E0–E2 ships)  
**Updated:** 17 August 2026  
**Prerequisite:** [MILESTONE_E0_E2.md](./MILESTONE_E0_E2.md) complete — single-tooth journey to export working end-to-end.

---

## Goal

Extend DentalSculptor from **single-tooth photo → sim export** to **multi-input clinical authoring**: IOS/CBCT segmentation, whole-jaw workflows, multi-tooth placement, and richer case libraries — while keeping the same pedagogical ownership research instrumentation.

---

## Phase map

| Phase | Deliverable | Weeks | Depends on |
|-------|-------------|-------|------------|
| **E3** | Anatomical segmentation (IOS + CBCT pipelines) | 4–6 | E2 export presets |
| **E4** | Multi-tooth placement + FDI-accurate sockets | 3–4 | E3 part labels |
| **E5** | Whole-jaw / oral cavity generation (multi-view or scan-first) | 4+ | E3, research spike |
| **E6** | Custom feed-forward edit model (from E0 revision dataset) | 6+ | 200+ labeled edits |
| **E7** | CBCT/X-ray import wizard + volume teaching cases | 3–4 | E3 DentalSegmentator |
| **E8** | Community case marketplace + institutional templates | 2–3 | Case wizard from E0 |

---

## E3 — Segmentation

### Tools

| Input | Pipeline | Output |
|-------|----------|--------|
| IOS STL/VTK jaw | [DentalModelSeg](https://github.com/DCBIA-OrthoLab/SlicerDentalModelSeg) | FDI per-tooth GLB parts |
| CBCT DICOM | [DentalSegmentator](https://github.com/gaudot/SlicerDentalSegmentator) | 5-class volume → meshes |
| µCT | [SlicerToothAnalyser](https://github.com/lukaskonietzka/SlicerToothAnalyser) | Tissue labels |
| Generated GLB | [ToothGroupNetwork](https://github.com/limhoyeon/ToothGroupNetwork) / CrossTooth | Research benchmark |

### Integration

- Modal or lab GPU FastAPI workers (same `dentalsculptor-ml` repo).
- `POST /jobs/segment` → populate Model Parts panel (replace mock `generateSegmentParts()`).
- Shared **part IDs** with Nano3D edit mask (select tooth before paint).

**Done when:** Real FDI labels in editor; export selected parts to STL.

---

## E4 — Multi-tooth placement

- Import segmented jaw or full arch IOS.
- Snap multiple authored teeth into FDI sockets.
- Collision-aware transform; merge layers for Simodont export.
- Extends E2 Placement Studio.

---

## E5 — Whole jaw from photos (research)

**Not promised for E0–E2.** Options to evaluate:

| Approach | Feasibility |
|----------|-------------|
| Multi-photo + photogrammetry | Medium; educator burden high |
| Scan-first (IOS import) | **Recommended** — align with E3 |
| Single photo generative full arch | **Low** — Hunyuan/TRELLIS not reliable |
| Template jaw + per-tooth generate | **Medium** — compositing workflow |

---

## E6 — Custom edit model

Train feed-forward editor from E0 `ModelRevision` dataset:

- Input: mesh latent + mask + instruction embedding
- Benchmark against Nano3D, Steer3D, Hunyuan3D-Buffano when weights public
- Target: &lt;30 s edits on L40S with preserved anatomy

---

## E7 — Multi-input teaching cases

| Input | Example case |
|-------|--------------|
| Panoramic X-ray | Impacted third molar identification (2D annotate, optional 3D from CBCT) |
| CBCT volume | Implant site assessment |
| IOS + photo | Crown prep on scan-aligned tooth |

Consent / PHI: on-prem GPU option for identifiable scans.

---

## E8 — Community & institution templates

- Publish case templates to Community Hub.
- Clone + adapt (pedagogical ownership: fork vs scratch).
- Institution-branded jaw libraries.

---

## Schema additions (E3+)

- `SegmentPart` model linked to `DentalModel`
- `InputAsset` with `type: photo | ios | cbct | xray`
- `CaseTemplate` DB table (move from static TS to editable)

---

## Success criteria (E3+ milestone)

1. Educator uploads IOS jaw → segmented teeth → edit one tooth → export to Simodont.
2. CBCT demo case runs on de-identified sample DICOM.
3. Model Parts panel drives edit masks and export selection.
4. Research dashboard shows segmentation + edit + export funnel.

---

## Related

- [IMPLEMENTATION_PLAN.md § Phase E](./IMPLEMENTATION_PLAN.md)
- [3D_EDITING_RESEARCH.md](./3D_EDITING_RESEARCH.md)
