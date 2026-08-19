# Jaw template assets — sources and E2 plan

**Updated:** 17 August 2026  
**Use:** Placement Studio (E2) — template jaw + FDI socket + merge export.

---

## Recommended stack (by license fit)

| Source | Content | License | E2 use | Notes |
|--------|---------|---------|--------|-------|
| **[Open-Full-Jaw](https://github.com/diku-dk/Open-Full-Jaw)** | 17 patients, maxilla + mandible + **individual teeth STL**, principal axes | Open dataset (paper: [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0169260722003911)) | **Primary E2 templates** | CBCT-segmented; dense STL in `dataset/Patient_*/input/*/`. Use **pipeline output** reduced meshes for performance. Tooth principal axes → FDI socket transforms. |
| **[Teeth3DS+](https://osf.io/xctdy/)** | 1800 IOS upper/lower jaws, FDI vertex labels | **CC BY-NC-ND 4.0** | Research / academic pilot only | NC = no commercial; ND = no derivatives — **verify with legal before production**. Good for socket calibration research. |
| **Simodont demo STL** | Patient Scan example file | Simodont Courseware bundled | **QA reference** | Teacher Manual mentions default demo STL for workflow testing — compare scale/orientation only. |
| **DTU FDI 16** ([doi:10.11583/dtu.23626650](https://doi.org/10.11583/dtu.23626650)) | 7,732 **single teeth** (not full jaw) | **CC BY-NC-SA 4.0** | Generation fine-tune, **not** jaw template | Open meshes; aligner attachment bias. |
| **Synthetic quadrant** | Procedural arch (Blender) | We own | Fallback if licensing blocked | Low realism; label "illustrative" |

---

## E2 implementation plan

### Phase 1 — Ship with Open-Full-Jaw (recommended)

1. Download `diku-dk/Open-Full-Jaw` dataset.  
2. Pick **2 mandible + 2 maxilla** reduced STL outputs (diverse anatomy).  
3. Decimate to &lt;200k tris for web viewer; store in **S3** `templates/jaws/v1/`.  
4. Extract **tooth principal axes** from repo metadata → JSON socket map per FDI.  
5. Gingiva mesh separate from teeth; hide patient teeth when placing user-generated tooth.

### Phase 2 — IOS-accurate sockets (E3, with license check)

- Teeth3DS+ jaws for FDI label accuracy on real IOS geometry.  
- Requires NC/ND license review for commercial DentalSculptor.

### Asset JSON schema (app)

```json
{
  "id": "open-full-jaw-p26-mandible",
  "label": "Adult mandible (Patient 26)",
  "meshUrl": "s3://.../templates/jaws/p26_mandible.stl",
  "units": "mm",
  "upAxis": "Y",
  "sockets": {
    "36": { "position": [12.4, 0.2, -3.1], "rotationEuler": [0, 0.12, 0], "scale": 1.0 }
  }
}
```

---

## DTU dataset vs jaw templates

Your link ([3Shape FDI 16 Meshes](https://data.dtu.dk/articles/dataset/3Shape_FDI_16_Meshes_from_Intraoral_Scans/23626650)) is **individual molar meshes**, ideal for:

- TRELLIS shape prior / benchmark  
- Placement **tooth** scale reference (mm, ISO 3950 axes)  

It is **not** a full-jaw template. Pair with Open-Full-Jaw for E2.

---

## Processing pipeline (Modal CPU worker)

```
Raw STL → trimesh repair → decimate (target tris) → axis normalize (Simodont Y-up)
  → upload S3 → register in templates manifest API
```

---

## Attribution (store in app About / docs)

- Open-Full-Jaw: cite Kamali et al., *Computer Methods and Programs in Biomedicine* (2022).  
- Teeth3DS+: Ben-Hamadou et al., MICCAI 2022 (if used).  
- DTU FDI 16: Ye et al., CC BY-NC-SA (fine-tune only).
