# Dental anatomy quality and practical teaching-case scope

## Decision

DentalSculptor should presently promise **external single-tooth morphology and surface-editing cases**, not a complete biological tooth. The generated model can support anatomy identification, localized Class I preparation geometry, occlusal lesion patterns, cusp fracture/chip variants, stains and conservative surface changes. Endodontic access, pulp exposure, caries hardness and tissue-selective drilling require segmented internal anatomy and material/haptic metadata and must be labelled unavailable rather than simulated by a uniform STL.

The reviewed screenshot shows a plausible tooth silhouette but an implausibly sharp, continuous occlusal ridge/groove transition. This is not chiefly a texture problem. A general image-to-3D model is reconstructing an unseen surface without tooth-number-specific rules, landmarks or occlusal context.

## How to make generated teeth anatomically credible

Do not rely on image-conditioned TRELLIS fine-tuning alone. Use a dental anatomy validation and correction stack:

1. **Classify and orient first.** Predict FDI tooth class, upper/lower arch, left/right, long axis and mesial/distal direction. Reject uncertain classifications or ask the educator to confirm.
2. **Canonicalize each training mesh.** Scale in millimetres, orient to a shared occlusal coordinate frame, repair topology, remove scans with preparation/restoration artefacts from the healthy cohort, and retain provenance.
3. **Create tooth-specific cohorts.** Train or adapt by tooth number/family. Mixing incisors, premolars and molars without conditioning encourages averaged anatomy.
4. **Annotate topology-aware landmarks and curves.** Cusps, cusp tips, central and triangular fossae, pits, developmental grooves, marginal ridges, triangular ridges, CEJ and root apices must be explicit targets—not inferred only through global Chamfer loss.
5. **Use a dental shape prior/refiner.** Generate with TRELLIS, register the result to a statistical or learned dental shape manifold, then refine the surface while preserving image evidence. The long-term custom model should be conditioned on tooth number, view, landmarks and—when available—adjacent/antagonist context.
6. **Use morphology-weighted losses.** Combine surface/normal/curvature losses with landmark distance, ridge-curve continuity, groove topology, cusp-count/class consistency, bilateral/asymmetry priors where appropriate, and minimum local thickness. Curvature-weighted Chamfer and gradient-weighted reconstruction are supported by recent morphology-aware crown work.
7. **Use negative and diseased examples deliberately.** Keep healthy anatomy, natural disease and synthetic teaching edits as separate labels. Diseased teeth help a pathology editor learn lesion/fracture appearance and placement, but must not contaminate the healthy base generator.
8. **Run a post-generation anatomy gate.** Measure cusp count/location, marginal-ridge continuity, groove graph, crown/root proportions, self-intersections, watertightness and scale. Low-confidence outputs return to regeneration or educator review.
9. **Use expert pairwise evaluation.** Dentists compare generated versus reference meshes blind, by tooth number, scoring global identity and local landmarks. Chamfer distance alone can be low while the occlusal anatomy is wrong.

### Recommended data organisation

```text
tooth_sample/
  mesh_raw
  mesh_canonical
  fdi_number, arch, side, age_band
  healthy | caries | fracture | restoration | preparation
  source: IOS | micro-CT | CBCT | curated CAD
  landmark_points
  ridge_and_groove_curves
  visible_surface_mask
  enamel/dentin/pulp labels when truly segmented
  license, consent, scanner, voxel/scan resolution
```

Use IOS/optical meshes for external crown truth, micro-CT for internal-layer research, and jaw scans for contacts/occlusion. A single isolated photograph cannot supply hidden root or internal anatomy truth.

## Teaching cases that are honest and useful now

| Case family | Current status | Useful variants |
|---|---|---|
| Tooth identification | Ship | Tooth number/family, view/orientation, healthy anatomical variation, labels hidden/revealed, compare normal variants |
| Class I preparation geometry | Ship as priority | Central pit, buccal/lingual pit where anatomically valid, groove extension pattern, 1–3 sites, coverage %, outline, depth, wall form, cusp/marginal-ridge preservation |
| Occlusal caries geometry/recognition | Ship with limitation | Pit/fissure site, lesion count, distribution, surface spread, cavitated/non-cavitated visual state, excavated geometry; clearly state STL has uniform material response |
| Cusp fracture/chipped enamel | Ship as priority | Named cusp, chip/oblique/large fragment, angle, depth, ridge involvement, one or multiple fragments |
| Non-carious wear and erosion | Add | Attrition facet, abrasion notch, erosion cupping; local subtractive geometry works without internal tissues |
| Morphology comparison | Add | Accessory cusp, cusp-size variation, groove-pattern comparison, root-number comparison when source proves roots; educator annotation rather than unconstrained generation |
| Simple crown reduction | Experimental | Local occlusal reduction and clearance review; full preparation requires calibrated axes, margins and antagonist context |
| Class II preparation | Experimental | Needs proximal contact and adjacent-tooth context; do not present an isolated-tooth result as validated |
| Endodontic access | Do not offer now | Requires pulp chamber, canal orifices, dentin/enamel boundaries and safe thickness relationships |
| Pulp exposure/internal resorption | Do not offer now | Requires volumetric internal anatomy and material layers |
| Haptic caries excavation | Do not claim from STL | STL conveys geometry only; disease-specific hardness must be represented by the target simulator or an accompanying supported material map |

Healthy tooth identification should not be padded with disease variants. Use anatomical variation—cusp/groove patterns, root configuration, side and arch—as the meaningful variants. Disease belongs in diagnosis/pathology exercises linked to the same healthy master.

## Class I and fracture authoring model

Each case variant should be generated from a structured recipe, not only prose:

```json
{
  "tooth": 46,
  "case": "class-i",
  "sites": ["central-fossa", "distal-pit"],
  "lesionCount": 2,
  "coveragePercent": 18,
  "depthMm": 1.5,
  "preserve": ["marginal-ridges", "cusp-tips"],
  "randomSeed": 2048
}
```

The mask supplies exact educator intent; the recipe supplies reproducibility and constraints. Generate combinations only when they are anatomically permitted for the confirmed tooth type. A named-cusp selector is better than a generic screen-space brush for fractures once tooth landmarks are available.

## Jaw-placement workflow

The Meshmixer workflow is a useful interaction model: jaw and tooth remain separate objects; the tooth is chosen by number, translated/rotated/scaled, visually checked, and combined only for export. DentalSculptor should improve this by supplying an FDI socket, automatic initial transform and autosaved revisions.

Implemented MVP flow:

1. **Place in jaw** sits in the editor header before **Create variant**.
2. User chooses upper/lower arch and an FDI socket.
3. The template supplies an initial socket transform.
4. Fine controls adjust three translations, three rotations and tooth scale; jaw scale is locked.
5. Every change is debounced and stored as a `jaw-placement` project version.
6. A clinical checklist covers long axis, occlusal plane, contacts, collision and real scale.
7. Future viewer work will render the licensed jaw template, snap using socket transforms, calculate collisions/contacts and merge a watertight STL only during export. Source tooth and placement metadata remain reversible.

## Sources

- Michael Scherer, Meshmixer tooth placement workflow: https://www.michaelschererdmd.com/moving-teeth-using-open-source-software/
- DCrownFormer+, morphology-aware crown generation and curvature/gradient losses: https://www.sciencedirect.com/science/article/pii/S1361841525002646
- Personalized dental crown design using prepared, adjacent and antagonist context: https://www.sciencedirect.com/science/article/pii/S1361841524003645
- Two-stage dental mesh landmark localization: https://pmc.ncbi.nlm.nih.gov/articles/PMC10547011/
- Tooth-axis estimation using clinician-annotated axes and landmarks: https://pmc.ncbi.nlm.nih.gov/articles/PMC13392359/
- Operative simulation assessment dimensions for Class I preparations: https://doi.org/10.1186/s12909-025-08045-2
- University of Iowa operative dentistry curriculum: https://catalog.registrar.uiowa.edu/dentistry/operative-dentistry/
