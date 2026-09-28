# DentalSculptor anatomical reconstruction recovery plan

Status: corrected R0 resume `ap-r7JVEthWhEqGAR0zCfzTYM` completed after wrapper
`ap-VmrYHCvIwQmoNR61eMZOm5` stopped after all 12
resumable oracle decodes but before final evidence assembly because one product
case has an unavailable apical-root proxy. The summary now reports paired
available root bands explicitly; no retry has been launched and no production
model mutation is authorized. The original wrapper
`ap-ACqDOMLkx4TSowhiaRpdqJ` stopped before model evaluation on a corrected
receipt-validation integration error and is not scientific evidence.

## 1. What the completed experiments establish

The E12 v7 full decoder, late-stage, output-only and block-3-only candidates all
failed the sealed crown/root/topology gates. Whole-tooth Chamfer sometimes
improved while crown accuracy or topology regressed. Therefore:

- the v7 parameter delta is rejected in full and in every tested late-stage
  decomposition;
- aggregate Chamfer is not an adequate promotion metric;
- changing a shared whole-tooth decoder is not a safe way to target crown detail;
- no current candidate is evidence of anatomical improvement.

These experiments used frozen latents produced from reference meshes. They test
the SC-VAE reconstruction boundary, not the complete product path from an input
image through image conditioning, shape-flow sampling and decoding. They cannot
identify the decoder as the dominant product bottleneck by themselves.

## 2. Revised scientific question

The product objective is not patient-specific recovery of an unseen root from a
single photograph. That is underdetermined. The defensible objective is:

> Generate a reproducible, tooth-family-correct and anatomically plausible whole
> tooth from one image, preserve the strong base root prior, and improve visible
> crown/occlusal morphology without regional or topology regression.

Patient-specific whole-tooth accuracy requires complementary observations such
as an intraoral scan for the crown and CBCT for the root.

## 3. Stage-attribution benchmark before more training

Use the same patient-disjoint cases, canonical transforms and hashes for three
paired paths:

1. **Representation ceiling:** reference mesh -> O-Voxel -> encoder -> decoder.
2. **Oracle latent decode:** sealed reference shape latent -> decoder.
3. **Product path:** deterministic render/photo -> image-conditioned shape flow
   -> decoder.

Evaluate all three with identical family-stratified metrics. The gap between 1
and 2 measures preprocessing/latent effects; the gap between 2 and 3 measures
image conditioning and generative inference. No component is fine-tuned until
this attribution report identifies the dominant gap.

Minimum gate: one incisor, canine, premolar and molar for integration, then at
least five patient-disjoint teeth per family for a decision. Repeat every product
generation at the fixed seed twice and at three preregistered seeds to separate
determinism from seed sensitivity.

## 4. Clinically meaningful evaluation

Keep the current engineering metrics, but make promotion depend on reviewed
landmarks and curves:

- crown: cusp count, cusp-tip position/height, central fossa, marginal and
  triangular ridge continuity, principal groove continuity, crown width/height,
  curvature-weighted surface distance and normal consistency;
- cervical: reviewed CEJ curve distance and seam continuity;
- root: root count, root length, apex position, furcation position for
  multirooted teeth, regional Chamfer/HD95 and volume ratio;
- mesh: watertightness target, connected components, boundary/non-manifold
  edges and self-intersections;
- expert: blinded pairwise preference and a fixed morphology rubric.

Canonical axial bands remain engineering proxies only. They must not be called
enamel, CEJ or root ground truth.

## 5. Recommended model architecture

Do not continue adapting the shared TRELLIS decoder. Use a two-part system:

1. **Base whole-tooth reconstruction:** frozen production TRELLIS.2 supplies the
   plausible whole tooth and the root prior.
2. **Crown-only residual refiner:** a small family-conditioned deformation or
   implicit-surface model refines only the crown. Its displacement is forced to
   zero below the reviewed CEJ and is smoothly tapered through a cervical
   transition band. The root vertices remain byte-identical to the base.

Inputs to the crown refiner are the base crown, input-image features, tooth
family/FDI identity and canonical pose. Outputs are bounded surface displacement
plus confidence. Low confidence returns the unchanged base.

This structure makes root preservation architectural rather than dependent on a
soft loss. It also allows high-fidelity crown-only meshes to improve crown detail
without pretending they contain root supervision.

## 6. Data roles and common representation

Convert every usable mesh to the same canonical training representation:
oriented surface points, normals, watertight signed/unsigned distance samples,
landmarks and region masks. Acquisition formats may differ; supervision roles
must not.

- ToothFairy: whole-tooth shape, root preservation and family priors after
  segmentation/QC. It does not provide IOS-grade crown detail.
- Teeth3DS and DTU FDI-16: crown/occlusal surface detail only. They provide no
  root target.
- Paired IOS+CBCT, when lawfully available: crown-root registration and CEJ seam
  validation; this is the strongest bridge data.
- Synthetic renders: multi-view, lighting/background and modest pose variation
  generated from each training mesh, while patient identity remains entirely in
  one split.

## 7. Short experiment ladder

### R0 — stage attribution (zero training)

Produce the three-path report in section 3. Stop if the product gap is not
primarily crown-local or if the representation ceiling itself is inadequate.

### R1 — deterministic/template crown baseline (zero learned updates)

Register a family/FDI template crown to the base crown using landmarks and a
bounded non-rigid deformation; taper displacement to zero at the CEJ. This is a
strong baseline and a fallback product path. It must improve at least three of
four families while every root/topology gate passes.

### R2 — small crown residual canary

Train only a compact crown refiner on the smallest balanced cohort. Freeze
TRELLIS entirely. First prove zero root displacement, finite gradients and exact
checkpoint reload; then run one update, then a four-family screen. Do not jump
to a long run.

### R3 — sample-efficiency ladder

Use nested patient-disjoint cohorts, for example 4, 8, 16 and 32 teeth per
family, with two fixed seeds. Stop increasing data when the lower confidence
bound no longer improves materially. Report every attempted cohort, not only
the best result.

### R4 — product-path confirmation

Run the winning crown refiner after the unchanged image-to-3D pipeline on held-
out synthetic renders and real educator images. Promotion requires both metric
gates and blinded expert review. A representation-only win is insufficient.

## 8. Alternative only if R0 identifies image conditioning as dominant

If oracle latent decoding is good but the product path is poor, adapt the image-
conditioned shape-flow model rather than the decoder. Use a small adapter/LoRA,
family-balanced multi-view renders, frozen SC-VAE targets and fixed-seed paired
evaluation. Root preservation still comes from crown-local output fusion, not a
global loss. Do not fine-tune both flow and decoder in the same first experiment.

## 9. Promotion and stop rules

A candidate advances only when all are true:

- median crown/occlusal improvement is positive with a bootstrap interval that
  does not support a meaningful regression;
- at least three of four tooth families improve and none exceeds the
  preregistered regression margin;
- every root, cervical and topology hard gate passes;
- raw repeatability and artifact hashes pass;
- blinded experts prefer the candidate without identifying root degradation;
- the exact model, data split, code revision, preprocessing and inference
  settings are sealed.

Failure at a gate returns to diagnosis. It does not authorize a neighboring long
training run.

## 10. Immediate next implementation

R0 is implemented and running on the 12 sealed Stage-1 cases (three per tooth
family). It reuses the existing image-conditioned unchanged-base report and
decodes each matching reference latent twice through the unchanged base decoder.
It committed resumable per-case artifacts and sealed
`stage_attribution_r0_v1.json`. Median crown error is 0.558929% of diagonal at
the unchanged reference-latent decoder boundary and 2.781558% on the unchanged
image-conditioned product path, a 4.8622x median gap. The measured dominant
boundary is image-conditioned generation. No optimizer, training run or
production deployment was used.

The next permitted experiment is R0.1, a zero-training decomposition of the
image-conditioned path. On the same 12 images and seeds, compare unchanged base
shape inference using (a) the sealed product sparse support and (b) sparse
support taken from the corresponding reference latent, then decode both through
the unchanged base decoder. If reference support closes most of the gap, target
image-to-sparse-structure inference; otherwise target image-conditioned shape
features. Do not fine-tune either stage until this attribution is sealed.

R0.1 launched as Modal app `ap-ZuFuPTDMa027ISzndE8n34`. Its preregistered
decision rule attributes sparse-structure dominance when reference support
closes at least 50% of the median crown gap, shape-feature dominance when it
closes at most 20%, and otherwise records a mixed boundary. These thresholds
were fixed before inspecting R0.1 outputs.

R0.1 completed with a median **0.932018** crown-gap fraction closed by reference
sparse support, and every one of the 12 cases had positive gap closure. The
family medians were 0.843775 (incisor), 0.946953 (canine), 0.918846 (premolar)
and 0.976262 (molar). The dominant measured sub-boundary is therefore
`image-to-sparse-structure`. The unchanged image-conditioned shape-feature model
and decoder recover anatomy close to the oracle once supplied correct support.

The next step is R0.2, not training: characterize predicted-versus-reference
sparse occupancy globally and within crown, cervical and root proxy bands, and
join those errors to the R0.1 downstream crown response. The earlier E3-E9
sparse-training failures mean an adapter is authorized for design only after
R0.2 identifies whether the base model misses occupancy, adds occupancy, shifts
extent, fragments components or misplaces poles in each family. Any later
adapter must be crown-weighted and retain an explicit root-preservation gate.

R0.2 completed with median exact-coordinate precision 0.2321, recall 0.2440,
IoU 0.1300 and centroid shift 1.6506 voxels. Crown is the weakest proxy band
(precision 0.1176, recall 0.1155, IoU 0.0438), with near-zero median crown recall
for canines and molars. The global pattern contains both missing and extra
occupancy, with extra predicted occupancy slightly dominant.

Before adapter training, R0.3 must separate coordinate-frame displacement from
true structural error. Search a preregistered bounded integer translation for
each predicted occupancy, then recompute global and regional overlap. If rigid
alignment closes much of the support gap, fix canonical pose/alignment first;
otherwise design a crown-weighted sparse-structure adapter with explicit root
non-regression. This avoids learning pose as anatomy.

R0.3 launched as CPU-only Modal app `ap-FZzY9WKgqZ0M0sSiH25bxo`. Before seeing
results, alignment dominance was fixed at at least 50% median crown-IoU error
closed, morphology dominance at at most 20%, and intermediate results as mixed.
The bounded search is +/-6 integer voxels per axis and cannot authorize an
optimizer run by itself.

R0.3 completed: bounded rigid translation closed only 0.025503 of median global
IoU error and -0.002182 of median crown IoU error. Although 11/12 cases selected
a nonzero shift, median crown overlap did not improve. The dominant residual is
therefore morphology and occupancy, not coordinate-frame alignment.

The next bounded implementation is R0.4, a zero-step sparse-adapter objective
qualification. Start from the exact frozen base sparse-structure flow and expose
only a small adapter/LoRA parameter set. Combine the official native flow target
with an explicitly crown-weighted support objective that penalizes both missing
and extra crown occupancy, while a frozen base teacher and hard regional gates
protect non-crown structure. R0.4 must establish finite nonzero gradients for
every adapter tensor, zero optimizer steps, exact frozen-state identity and
deterministic objective receipts. It may authorize one integration update, but
cannot itself claim anatomical improvement.

R0.4 phase A completed on the sealed 12-case cohort in Modal app
`ap-sGVyDCq1E5yuEsCG7zZrec`. All 12 objective probes passed, covering 2,939
missing and 2,699 extra crown-proxy voxels; every rank-4 adapter tensor received
a finite nonzero total gradient and every case had an active non-crown
preservation gradient. No optimizer step ran. This authorizes phase B model
integration, not training: the next probe must wire the adapter into the real
frozen sparse flow and prove complete adapter gradients and byte-identical
frozen model states before one update can be considered.

## Sources informing the revision

- Microsoft TRELLIS.2 repository and official 512 SC-VAE fine-tuning config:
  https://github.com/microsoft/TRELLIS.2
- O-Voxel flexible dual-grid conversion and decoding:
  https://github.com/microsoft/TRELLIS.2/blob/main/o-voxel/o_voxel/convert/flexible_dual_grid.py
- High-fidelity tooth reconstruction by IOS/CBCT fusion and a class-specific
  implicit prior: https://arxiv.org/abs/2601.15358
- Dental Mesh Completion, context-conditioned crown reconstruction with normals:
  https://arxiv.org/abs/2501.04914
- MADCrowner, margin-aware template deformation/refinement:
  https://arxiv.org/abs/2603.04771
- Crown morphology landmarks measurable from 3D scans:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC11088106/
