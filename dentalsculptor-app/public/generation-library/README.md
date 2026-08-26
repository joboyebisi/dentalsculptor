# Generation image library

Teaching photos for **Browse library** (landing, New project, editor Source).

## Add images (for maintainers)

1. Copy approved PNG/JPG files into this folder (`public/generation-library/`).
2. Ask the team (or use vision review) to label each image:
   - **title** — short educator-friendly name
   - **toothType** — `incisor` | `canine` | `premolar` | `molar`
   - **fdiHint** — best-guess FDI number (e.g. `36`) if known from source metadata
   - **credit** — licensing / e-resource attribution
3. Add an entry to `manifest.json` per file.

**Do not** add tooth numbering charts (ISO/FDI diagrams) — those belong in `public/dental/` for the case wizard only.

## User workflow

| Step | What happens |
|------|----------------|
| **Browse library** | User picks a curated photo (same as uploading locally) |
| **Generate 3D** | No tooth number required |
| **Case wizard** (optional) | User confirms FDI on the chart; library `fdiHint` **pre-fills** tooth number + type when present |

We do **not** auto-detect FDI from pixels yet — library metadata is a hint; educators can change it in the case wizard.

## Example manifest entry

```json
{
  "id": "lower-molar-occlusal-caries",
  "title": "Lower molar — occlusal caries",
  "toothType": "molar",
  "fdiHint": "36",
  "path": "/generation-library/lower-molar-occlusal-caries.jpg",
  "credit": "University e-resource — used with permission"
}
```

After commit + Vercel deploy, images are served at `https://<your-app>/generation-library/<filename>`.
