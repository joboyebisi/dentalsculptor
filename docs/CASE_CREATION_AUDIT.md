# Case creation execution audit

**Updated:** 29 August 2026

## Camera/mask execution correction

The browser and geometry worker now share one tested projection convention.
Three.js camera arrays are converted from column-major order before NumPy matrix
multiplication. Narrow fracture-line masks use a small screen-space tolerance so
decimated meshes do not miss a valid boundary between projected vertices. An
off-tooth mask still selects nothing and fails safely.

For guided cases, the case preset owns the operation. The compact toolbar does
not expose Add/Remove/Replace switching, preventing a fracture or preparation
case from contradicting its recipe. Cusp fracture alone adds a line tool; the
other cases retain the same Goal → Target → Preview → Create layout with their
case-specific target copy.

## Shared interaction contract

Every case begins from the same four-step contract:

1. **Goal** — selected in the case wizard and summarized beside the source image.
2. **Target** — rotate the tooth, then paint or mark only the relevant anatomy.
3. **Preview** — inspect a case-labelled 2D proposal; refine the target if wrong.
4. **Create** — generate a reversible variant from the immutable master, review it,
   then accept or discard it before save, publish, share or export.

Only the target wording, preset parameters and execution technique change. The
location and order of the controls do not.

## Pilot cases

| Case | Default executable preset | Technique | Guided target | Result contract | Current limitation |
|---|---|---|---|---|---|
| Tooth identification | None | Annotation | Mark an anatomical point/region | Labels on unchanged master | Annotation authoring in the current CAM viewer is not complete; do not route this case into geometry editing. |
| Cusp fracture | Oblique cusp fracture | Local Boolean removal | Paint enamel fragment to remove | Visibly missing localized cusp fragment | Imported non-watertight meshes may use localized deformation fallback. |
| Simple Class I | Standard Class I | Local Boolean removal | Paint preparation outline | Localized occlusal cavity | Depth is a requested recipe value, not yet a calibrated simulator measurement. |
| Endodontic access | Conservative access | Local Boolean removal | Paint external access outline | External opening only | Does not assert or generate true pulp/canal anatomy. |
| Caries appearance | Visual lesion for smooth-surface; excavation for occlusal | Vertex material or Boolean removal | Paint lesion area | Visual lesion or excavated cavity | Visual caries is not soft tissue and has no haptic hardness map. |
| Crown reduction | Occlusal reduction | Local Boolean removal | Paint surfaces to reduce | Broad localized reduction | Experimental until clearance measurements and repeatability gates pass. |

## Submission and ownership correction

The Vercel 403s on `/edit-jobs` occurred after successful template and preview
requests. The browser submitted the authenticated `/api/projects/{id}/model`
proxy while the API compared it only with the stored external URL.

The API now:

- recognizes the authenticated project proxy;
- ignores the browser's model choice for a case variant;
- loads an existing immutable `master-model` snapshot server-side, or establishes
  one from the project model on the first variant;
- recovers the storage key and issues a fresh signed URL;
- submits that server-owned URL to the worker.

This removes the stale/proxy URL mismatch and prevents a client from selecting a
different model as a variant source.

## Release gates per case

Before enabling a case in the pilot, run at least ten fixed-input attempts and
record:

- edit-job HTTP status and worker completion;
- visible target overlap;
- protected-region stability;
- valid non-empty GLB;
- bounds drift and material preservation;
- accept and reject behavior;
- exported GLB/STL/PLY validation;
- blinded educator acceptance.

A geometry case stays experimental until at least 8/10 results are accepted and
there is no severe protected-region failure. Tooth identification requires a
separate annotation-authoring acceptance test rather than this geometry gate.
