# Fine-tuning plan — DTU FDI 16 + dental text

**Updated:** 17 August 2026  
**Dataset:** [3Shape FDI 16 Meshes from Intraoral Scans](https://doi.org/10.11583/dtu.23626650) (7,732 meshes; train/val/test 4844/1465/1423)  
**License:** **CC BY-NC-SA 4.0** — academic/research OK; confirm commercial use with DTU/3Shape.

---

## What the dataset contains

Per sample:

- `*_mesh.ply` — segmented FDI 16 (maxillary first molar) triangle mesh  
- `*_point_cloud.ply` — vertices + facet midpoints  
- `*_curvature_edgedistance.dat` — curvature + edge distance features  

Meshes are **open** (interproximal boundaries), **mm scale**, axes: x → neighbor FDI 17, y → occlusal, z → buccal-lingual. Bias: aligner patients, attachments common.

**Good for:** shape generation quality, real IOS statistics, orientation prior.  
**Not included:** paired clinical photos for every mesh (limits image→3D fine-tune unless you render synthetic views).

---

## TRELLIS fine-tune (shape) — E3 research track, not E0 blocker

Microsoft TRELLIS ships `train.py` + TRELLIS-500K-style layout ([github.com/microsoft/TRELLIS](https://github.com/microsoft/TRELLIS)). No official LoRA; use **full or partial fine-tune** on Modal multi-GPU.

### Data prep pipeline

1. **Render multiview images** from each PLY (Blender headless or TRELLIS dataset toolkit — 20–40 views).  
2. **Convert meshes** to TRELLIS sparse-structure + SLat training format.  
3. **Filter** samples with heavy aligner attachments (optional QC score).  
4. **Augment:** slight rotation, lighting — preserve occlusal axis convention.  
5. **Hold out** official test split for benchmark vs base TRELLIS.

### Success metrics

- Chamfer / F-score vs held-out IOS meshes  
- Educator blind preference vs base TRELLIS on 20 photo inputs  
- Generation time unchanged within 20%

### Cost rough order

- Data prep: ~CPU hours on Modal  
- Fine-tune: multi-day A100 run — budget **$200–800** from your Modal credits; spike on 500 meshes first.

**E0 decision:** Ship **base TRELLIS** on Modal; start DTU fine-tune **in parallel week 3–4** if base mesh quality insufficient on molars.

---

## Nano3D fine-tune

Nano3D is training-free on TRELLIS latents — **no standard fine-tune**. Improvements come from:

1. Better **TRELLIS** dental shapes (above).  
2. Better **2D inpaint** with dental prompts.  
3. **Case 3** route (edited image + GLB) rather than direct GLB edit.

---

## "Fine-tune for text" — what is actually feasible

| Goal | Approach | Milestone |
|------|----------|-----------|
| Model understands "mesiobuccal cusp" | **Prompt expansion layer** — dental glossary maps colloquial → anatomical terms before inpaint/TRELLIS | E0 (software) |
| Text → correct edit region | **Mask UI** (user paint) + optional E3 **FDI part IDs** | E0 / E3 |
| Text → 3D without mask | Steer3D / future custom editor — benchmark E3 | E3 |
| Qwen-Image dental inpaint | LoRA on inpaint model with paired (mask, prompt, edit) from accepted revisions | E6 |
| TRELLIS text conditioning | TRELLIS-image-large is **image-conditioned**, not text-first — low ROI for text FT | Defer |

### Dental text layer (implement in E0 — no GPU cost)

Create `lib/dental-prompt-glossary.ts`:

```text
"remove decay" → "remove dark carious dentin in the central occlusal fossa, preserve enamel rim"
"endo access" → "open pulp chamber roof through occlusal surface, expose canal orifices"
```

Log original + expanded prompt in `ModelRevision.metadata` for research and future LoRA dataset.

### Revision dataset for E6 custom editor

Every accept/reject edit saves:

- mask PNG, camera, source GLB, result GLB  
- user prompt + expanded prompt  
- case template ID, FDI (when E3 live)  
- educator accept/reject + reason  

Target **200+ accepted edits** before custom model training.

---

## License checklist before training

- [ ] Confirm CC BY-NC-SA allows your **doctoral/commercial** deployment path  
- [ ] Document attribution in app + model card  
- [ ] Do not redistribute fine-tuned weights if SA clause requires share-alike  

---

## Recommended priority

1. **E0:** Glossary + prompt expansion (immediate).  
2. **E0 spike:** Base TRELLIS + Nano3D benchmark on 20 DTU-held-out renders.  
3. **E3:** DTU TRELLIS fine-tune if benchmark fails clinical acceptance.  
4. **E6:** Inpaint LoRA from revision pairs; evaluate Steer3D for text-only edits.
