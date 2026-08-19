# Haptic export strategy — visual caries vs drillable feel

**Updated:** 17 August 2026  
**Problem:** Nano3D/TRELLIS edits can make caries *look* correct in VR, but Simodont/SimtoCARE/Virteasy need specific data for *tactile* caries simulation.

---

## Platform reality (from vendor docs)

| Platform | Custom STL/PLY import | Multi-tissue haptics (enamel / dentin / soft caries) |
|----------|----------------------|------------------------------------------------------|
| **Simodont** | Yes — Models or Patient Scan workflow | **No** from STL alone. Uniform hardness throughout ([Teacher Manual v4.18 §6](https://www.simodontdentaltrainer.com/wp-content/uploads/2024/02/Simodont_Courseware_v4.18_Teacher_Manual_FINAL.pdf)). PLY adds surface color pushed ~1 mm inward; hardness still uniform. |
| **Simodont native cariology** | Built-in micro-CT library | **Yes** — enamel, dentin, pulp, caries, restorations with tissue-specific resistance |
| **TrueTeethLab** (Nissin) | Simodont-specific format from DICOM/µCT | **Yes** — AI tissue segmentation → hardness layers |
| **SimtoCARE** | STL/PLY → voxelized drillable model | **Limited** — drillable uniform material; literature notes difficulty replicating enamel vs dentin hardness on custom imports |
| **Virteasy** | STL exercises | Geometry + platform-defined haptics; custom STL is prep practice, not soft caries |
| **Meta Quest / WebXR** | GLB | **Visual only** — no haptics |

**Conclusion:** A generative "remove caries" edit produces **geometry for visual teaching and prep form practice**, not authentic soft-carious *feel* on custom import.

---

## Three export tiers (product language)

Educators must see this **before export**, not discover it in the sim lab.

| Tier | Label in UI | What we export | Haptic outcome | Milestone |
|------|-------------|----------------|----------------|-----------|
| **A — Geometry prep** | "Prep practice (uniform feel)" | Watertight STL/PLY, mm | Drillable; **same hardness everywhere** | **E0–E2** |
| **B — Visual / VR teaching** | "Anatomy & pathology (VR)" | GLB + optional STL | Look-only or uniform drill | **E0–E2** |
| **C — Full haptic caries** | "Tissue-realistic haptics" | Simodont native / TrueTeethLab / voxel volume | Soft caries vs enamel | **E3+** (CBCT path) |

### Case template mapping

| Template | Tier A (Simodont STL) | Tier B (Quest) | Tier C (future) |
|----------|----------------------|----------------|-----------------|
| Anatomy ID | Optional | **Primary** | — |
| Occlusal caries excavation | Prep cavity **shape** only; label "uniform haptics" | Show lesion visually | TrueTeethLab from µCT |
| Class I / II prep | **Primary** | Secondary | — |
| Crown / endo access | **Primary** | Secondary | CBCT TrueTeethLab for pulp |

Update case wizard copy: *"Caries templates train cavity design and visual recognition. For soft caries tactile feedback, pair with Simodont built-in cariology cases or import via TrueTeethLab (CBCT)."*

---

## Recommended educator workflows

### Workflow 1 — DentalSculptor geometry → Simodont prep (E0–E2)

1. Generate + edit tooth in DentalSculptor.  
2. Export **Simodont preset** (STL, watertight, mm).  
3. Import via Simodont **Models → Import STL**.  
4. Assign to course as **intra-oral scan style** prep case.  
5. Student practices **cavity outline and depth** with uniform resistance.

### Workflow 2 — Visual caries in VR (E0–E2)

1. Same authored model.  
2. Export **Meta Quest GLB** or use `/xr/[id]`.  
3. Learning objective: recognize extent of lesion, plan access — **no haptic claim**.

### Workflow 3 — True haptic caries (E3+ / partner)

1. Obtain µCT or CBCT of extracted tooth OR use Simodont commercial cariology library.  
2. **TrueTeethLab:** DICOM → Simodont model with enamel/dentin/pulp hardness.  
3. DentalSculptor links case metadata + learning objectives; geometry optional for comparison slides.

### Workflow 4 — Research voxel blocks (long-term)

Sheffield/Moog approach: custom software builds **voxel density stacks** (0–255) for enamel, dentin, caries gradients → Simodont-compatible volume ([JSS 2017](https://www.journalsurgicalsimulation.com/contents/volume4/JSS170006/)). Not in E0–E2 scope — requires proprietary Simodont volume format partnership.

---

## Export wizard UX requirements (revision)

1. **Platform card** shows haptic tier badge: `Geometry only` | `Native sim library` | `VR visual`.  
2. **Amber disclosure** on Simodont/SimtoCARE when tier A.  
3. **Link** to Simodont cariology catalog + TrueTeethLab for tier C.  
4. **Research event** `EXPORT_REQUESTED` includes `{ tier, platform, hapticRealism: "uniform" | "multi-tissue" }`.

---

## Milestone impact

**No delay to E0–E2**, but **rename and scope case templates**:

- "Caries excavation" → **"Caries cavity design (geometry)"**  
- Add learning objective: distinguish visual pathology from haptic training  
- E3 adds **CBCT → TrueTeethLab handoff** export preset  
- E3 adds optional **Simodont case ID** field to link native haptic library tooth

---

## SimtoCARE / Virteasy notes

- **SimtoCARE:** Voxelizes STL internally (~0.1 mm³ for detail); still single-material feel for custom scans ([IP page](https://www.simtocare.com/intellectual-property/)).  
- **Virteasy:** STL for exercise import and 3D print; haptics defined in Unreal scene — custom mesh is geometry carrier.

Both remain valid **Tier A** export targets with same disclosure.
