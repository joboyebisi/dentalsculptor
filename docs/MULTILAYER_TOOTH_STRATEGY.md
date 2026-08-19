# Multilayer tooth strategy — enamel, dentin and pulp

**Status:** Critical research workstream  
**Updated:** 19 August 2026

## Decision

DentalSculptor needs one tissue-aware model contract, but two different sources of
anatomy:

1. **Photo-generated teaching teeth:** TRELLIS supplies only the external surface.
   Internal enamel, dentin and pulp must be clearly labelled as anatomically
   plausible template anatomy, not patient-specific reconstruction.
2. **Measured patient/ex-vivo teeth:** CBCT or preferably micro-CT supplies a
   calibrated volume from which tissue labels can be segmented.

A single RGB photograph contains no evidence about pulp chamber shape, canal
configuration or enamel-dentin boundaries. No generation setting or additional
GPU can recover those hidden structures reliably.

## Required representation

Use a volumetric label field as the authoritative editable representation:

```text
0 background
1 enamel
2 dentin
3 pulp
4 caries / softened tissue
5 restoration
```

The labels must partition the tooth volume without gaps or overlapping solids.
Surface meshes are derived artifacts:

- `enamel.glb` / `enamel.stl`
- `dentin.glb` / `dentin.stl`
- `pulp.glb` / `pulp.stl`
- one GLB with separate named primitives and material IDs for web/VR viewing
- a labelled voxel volume or simulator-specific package for tissue haptics

GLB can retain multiple visual materials. STL cannot store tissue identity or
haptic properties, so a multilayer STL export must be a ZIP of named files and
must not claim native multilayer haptics.

## Photo-to-multilayer prototype

### Inputs

- accepted, watertight outer tooth mesh;
- tooth class / FDI number selected or inferred with educator confirmation;
- calibrated crown-root length in millimetres;
- matching validated internal template from a micro-CT template library.

### Algorithm

1. Repair, orient and scale the TRELLIS surface.
2. Estimate the long axis and cemento-enamel junction; require educator review.
3. Voxelize the closed tooth at 0.1–0.2 mm or construct an equivalent signed
   distance field.
4. Register the tooth-type template to the generated exterior using landmarks,
   cage deformation and non-rigid refinement.
5. Warp the template pulp/canal and enamel-dentin boundary into the generated
   tooth while enforcing minimum wall thickness and containment.
6. Rasterize mutually exclusive tissue labels inside the outer surface.
7. Apply topology checks: pulp contained by dentin, dentin contained by tooth,
   no disconnected floating tissues, minimum thickness constraints.
8. Extract display/export meshes with marching cubes, repair and decimation.
9. Store the template ID, transform, constraints and educator approval as
   provenance.

Simple uniform inward offsets are acceptable only for an early visual prototype.
They are not adequate for endodontic training because real enamel thickness,
pulp horns and root canals are not uniform offsets of the outer surface.

## Scan-to-multilayer pipeline

1. Accept de-identified DICOM/NIfTI with physical voxel spacing.
2. Crop and resample the tooth region while preserving real scale.
3. Segment tooth instances and tissue labels.
4. Review labels slice-by-slice; permit manual correction.
5. Convert the corrected label map into watertight surfaces.
6. Validate Dice/surface distance where reference labels exist and record scan
   resolution, model version and corrections.

Micro-CT is the preferred source for fine enamel and canal anatomy. CBCT can be
used, but its typical resolution and artifacts can make enamel/dentin separation
less reliable. TrueTeethLab specifies 200-micron input as a minimum and exports
a proprietary Simodont package with enamel, dentin and pulp.

Useful research sources:

- [TrueTeethLab](https://www.simodontdentaltrainer.com/trueteethlab/) — DICOM
  tissue segmentation and proprietary Simodont export.
- [Multi-layered virtual tooth model for haptic training](https://doi.org/10.4012/dmj.2010-082)
  — tissue-specific haptic parameters from micro-CT-derived anatomy.
- [Pulpy3D](https://ditto.ing.unimore.it/pulpy3d/) and
  [ToothFairy3](https://toothfairy3.grand-challenge.org/dataset/) — CBCT pulp
  and tooth segmentation research data; licences must be checked before product
  training.
- [ACTA-DIRECT v2](https://dare.uva.nl/id/fdc3f39f-8d3f-460f-8937-6b6966eebbdc)
  — 227 extracted-tooth micro-CT scans with caries annotations.
- [ZMK tooth cohort](https://github.com/habi/zmk-tooth-cohort) — reproducible
  micro-CT root-canal analysis examples.

## Editing contract

Editing must operate on tissue labels, not only the rendered outer mesh:

- preparation/removal subtracts the tool path from every intersected tissue;
- caries editing changes selected voxels to a softer material label;
- pulp exposure is detected when the preparation intersects the pulp label;
- protected-region error is measured separately per tissue;
- accepting an edit creates an immutable labelled-volume revision and regenerates
  the surface meshes.

Nano3D can propose or modify the exterior appearance, but it does not provide
clinically trustworthy internal tissue anatomy. Its result must therefore be
reconciled with the tissue volume and revalidated.

## Simulator constraint

Simodont can import ordinary STL patient scans, but published workflows report
monochromatic, homogeneous hardness for those imports. Native enamel/dentin/pulp
haptics are provided through Simodont content or TrueTeethLab's proprietary
format. Similar limitations apply to generic custom imports on other trainers.

Before claiming multilayer haptics, obtain and test each vendor's material
contract:

- accepted geometry/volume format;
- tissue/material identifier mapping;
- stiffness, damping or density parameters;
- cutting/deletion behaviour;
- scale, orientation and voxel-resolution limits.

## Delivery sequence

1. **M0 visual prototype:** generated exterior + clearly labelled synthetic
   dentin/pulp templates; GLB layer toggle and ZIP of named meshes.
2. **M1 editable tissue volume:** voxel/SDF label field, tissue-aware cutting,
   containment and exposure metrics.
3. **M2 measured anatomy:** micro-CT/CBCT segmentation and educator correction.
4. **M3 haptic integration:** vendor-specific material export validated on each
   target machine.
5. **M4 research validation:** expert anatomy ratings, layer surface error,
   topology, haptic discrimination and learning-outcome evaluation.

