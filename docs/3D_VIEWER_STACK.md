# 3D viewer & editor stack — Pascal and alternatives

**Updated:** 17 August 2026  
**Current app:** React Three Fiber + Drei + Three.js WebGL (`cam-model-viewer.tsx`).

---

## Pascal Editor ([pascalorg/editor](https://github.com/pascalorg/editor))

MIT, ~18k★. Built for **architectural BIM**, not dental — but patterns transfer.

| Pascal package | DentalSculptor equivalent | Adopt? |
|----------------|---------------------------|--------|
| `@pascal-app/core` — Zustand + Zundo undo, scene graph | Custom editor state; Zundo planned Phase B | **Patterns only** — adopt Zundo for revisions |
| `@pascal-app/viewer` — R3F WebGPU viewer | `cam-model-viewer.tsx` WebGL | **Defer WebGPU** — Safari/Quest browser gaps |
| `three-bvh-csg` — boolean cutouts | E2 jaw merge, future prep boolean | **E2** — evaluate for merge/export |
| Selection outline, SFX | Partially done (`sfx-bus`, emissive select) | **Continue** Pascal polish checklist |
| Spatial grid / snap | E2 FDI socket snap | **Inspire** Placement Studio |

**Do not embed** Pascal packages wholesale — domain schema is walls/levels, not teeth. **Cherry-pick:** Zundo undo, export toasts, selection UX, CSG for merge.

---

## Dental-specific open source

| Library | Use case | Fit |
|---------|----------|-----|
| **[three.js](https://threejs.org/) + [R3F](https://docs.pmnd.rs/react-three-fiber)** | Viewport, GLB/OBJ, WebXR | **Current — keep** |
| **[drei](https://github.com/pmndrs/drei)** | OrbitControls, Environment, Gizmo | **Current — add TransformControls E2** |
| **[three-mesh-bvh](https://github.com/gkjohnson/three-mesh-bvh)** | Fast raycast for mask paint | **E0 edit mode** |
| **[three-bvh-csg](https://github.com/gkjohnson/three-bvh-csg)** | Boolean merge tooth+jaw | **E2 export** |
| **[vtk.js](https://kitware.github.io/vtk-js/)** | CBCT volume slice (E7) | E3+ |
| **[ITK-Wasm](https://wasm.itk.org/)** | DICOM read in browser | E7 |
| **SuperSplat** | Manual 3DGS edit | Not for GLB dental — skip |
| **Open3D / trimesh** (Modal CPU) | Watertight STL repair | **E1 export** |

---

## Mask paint best practice (E0)

1. Render model to offscreen buffer at fixed camera (`preserveDrawingBuffer`).  
2. Paint on 2D canvas overlay; store mask PNG.  
3. Raycast (`three-mesh-bvh`) optional 3D preview of protected region.  
4. Never edit mesh vertices directly in browser for generative workflow — keep Nano3D as source of truth.

Reference: Nano3D Case 3 needs **approved 2D reference**, not mesh sculpt.

---

## Rendering teeth (best practices)

| Topic | Practice |
|-------|----------|
| Materials | PBR with low metalness, `Environment` studio preset — done in `model-material-utils.ts` |
| Scale | Normalize on load; store mm scale factor in `meshData` for export |
| Lighting | Hemisphere + directional; avoid flat black albedo |
| Teeth count | Single mesh per revision until E3 segmentation |
| Performance | Draco GLB for Quest; decimate on export not in editor |

---

## WebXR (Quest)

- In-app: `/xr/[id]` with `@react-three/xr` or Three WebXRManager.  
- Export GLB in **meters** (×0.001 from mm).  
- Pascal WebGPU **not** used — Quest browser WebGL2 path.

---

## Undo / revision model

| Approach | Scope |
|----------|-------|
| **Immutable revisions** (v1, v2, v3) | Generative edits — **primary** |
| **Zundo** | UI state, camera, mask strokes before submit | 
| **Non-destructive** | Case template + placement transforms JSON |

Aligns with research audit — never overwrite source GLB.

---

## Decision summary

- **Keep** R3F + Drei + Three.js WebGL for E0–E2.  
- **Add** three-mesh-bvh (paint), TransformControls (E2), trimesh on Modal (E1).  
- **Borrow UX** from Pascal (SFX, undo, selection) — already in IMPLEMENTATION_PLAN §10.  
- **Do not** migrate to Pascal SDK or WebGPU until post-pilot.
