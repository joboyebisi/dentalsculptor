# TRELLIS.2 GPU — step-by-step setup

Real image→3D on Modal needs **RMBG + DINOv3 access on Hugging Face** (TRELLIS itself is open), **one HF token**, then deploy.

---

## Part A — Hugging Face (browser)

Log in at [huggingface.co](https://huggingface.co).

### Step A1 — TRELLIS.2-4B (main model) — **no accept button needed**

Open: https://huggingface.co/microsoft/TRELLIS.2-4B

Your page (MIT license, **Model card** / **Files and versions** tabs, **Use this model** button) means **you already have access**. There is no “Agree and access” step for this repo — it is **open (MIT)**.

**Sanity check:** click **Files and versions** → you should see weight files (e.g. `.safetensors`), not a login wall.

### Step A2 — RMBG-2.0 (background removal) — **form required**

Open: https://huggingface.co/briaai/RMBG-2.0

You should see: **“Fill in this form to immediately access the model for non commercial use”**.

1. Log in if prompted  
2. Fill the short form (name, accept license)  
3. Submit — approval is usually **instant**

### Step A3 — DINOv3 (vision encoder) — **form + wait**

Open: https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m

You should see: **“You need to agree to share your contact information to access this model”**.

1. Click through, fill name, affiliation, job title, accept Meta license  
2. Submit  
3. **Wait for approval email** from Hugging Face (Meta reviews — can be **minutes to a few days**)

You cannot run full TRELLIS on Modal until **RMBG + DINOv3** are approved (TRELLIS weights download automatically; these two are pulled by the pipeline at runtime).

### Step A4 — Nano3D — **not on Hugging Face for this step**

**Nano3D is not listed under TRELLIS** and you do **not** need a Hugging Face model for it right now.

| Piece | Where it lives | When we use it |
|-------|----------------|----------------|
| **TRELLIS.2** | HF `microsoft/TRELLIS.2-4B` | **Now** — image → 3D generate |
| **DINOv3 + RMBG** | Separate HF repos | **Now** — inside TRELLIS preprocess (automatic) |
| **Nano3D** | GitHub `JAMESYJL/Nano3D` | **Later** — mask + edit jobs on Modal (E0 edit spike) |

### Step A5 — Create a read token

1. Open https://huggingface.co/settings/tokens  
2. Click **Create new token**  
3. Name: `dentalsculptor-modal`  
4. Type: **Read** (fine-grained → Repositories: read is OK; classic Read token also works)  
5. Click **Create**  
6. **Copy the token** — it starts with `hf_` and is shown **once**

---

## What DINOv3 and RMBG actually do (you never touch them directly)

When a user uploads a tooth photo in DentalSculptor, TRELLIS runs **inside Modal** as one pipeline:

```text
Your PNG/JPG
    → RMBG-2.0 removes background (so the tooth is isolated)
    → DINOv3 “looks at” the image (vision features for 3D shape)
    → TRELLIS.2-4B builds the 3D mesh + textures
    → GLB returned to the app
```

You do **not** add separate API calls for DINOv3 or RMBG in the Next.js app. Hugging Face access is only so Modal can **download those weights** when the container starts.

**RMBG note:** CC BY-NC 4.0 (non-commercial). Fine for teaching/research; commercial Simodont courses may need a different background-removal step later.

---

## Part B — Paste token in `.env` (~30 seconds)

1. Open `dentalsculptor-app/.env`  
2. Find the line `HF_TOKEN=`  
3. Paste your token after the `=`:

```env
HF_TOKEN=hf_paste_your_token_here
```

4. Save the file  

**Do not commit or paste this token in chat.** Keep it only in `.env` (already gitignored).

---

## Part C — Run deploy (agent or you)

From PowerShell at repo root:

```powershell
.\dentalsculptor-ml\scripts\setup-trellis-gpu.ps1
```

This script will:

1. Verify your HF token  
2. Create Modal secret `huggingface`  
3. Deploy with `TRELLIS_GPU=1` (first time: **20–40 min** CUDA image build)

Or tell the agent: **“HF token is in .env, run the TRELLIS setup script”**

---

## Part D — Test in the app

1. Restart dev server:

```powershell
cd dentalsculptor-app
npm run dev
```

2. Upload a single-tooth PNG/JPG → Generate  
3. First request may take **2–3 minutes** (cold start + model load)  
4. Later requests ~**10–30 seconds**

**Success:** server log shows:

```text
[ml-provider] modal generate source=modal-trellis2-gpu pipeline=512
```

**Still placeholder:** `source=modal-pipeline-v0` means GPU deploy did not run yet.

---

## Manual commands (if you prefer)

```powershell
modal secret create huggingface HF_TOKEN=hf_your_token
cd dentalsculptor-ml
$env:PYTHONIOENCODING = "utf-8"
$env:TRELLIS_GPU = "1"
python -m modal deploy -m modal_app.app
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Gated model page, no files | RMBG: submit form. DINOv3: wait for approval email |
| `401` / invalid token | New token at huggingface.co/settings/tokens |
| `Secret huggingface not found` | Run setup script or `modal secret create` |
| Deploy fails on GPU quota | Check modal.com/settings for A100 access |
| Build timeout | Re-run deploy; Modal caches layers |
| 10+ min first generate | Normal cold start |

---

## Reference

CUDA image: `dentalsculptor-ml/modal_app/images/trellis_gpu.py`  
Adapted from [dnouri/TRELLIS.2 modal-integration](https://github.com/dnouri/TRELLIS.2/tree/modal-integration)
