# AWS S3 setup for DentalSculptor

**Purpose:** Store GLB/STL meshes, masks, and job I/O from Modal workers. Supabase Storage stays for thumbnails and small assets; S3 handles large 3D files.

---

## 1. Create the bucket

1. Sign in to [AWS Console](https://console.aws.amazon.com/) (use the account with your credits).
2. **S3** → **Create bucket**
3. Settings:
   - **Name:** `dentalsculptor-assets-prod` (globally unique — add suffix if taken)
   - **Region:** `eu-west-1` (match Supabase EU if possible)
   - **Block public access:** ON (recommended — use signed URLs)
   - **Versioning:** optional
4. Create bucket.

---

## 2. CORS (for browser signed downloads)

Bucket → **Permissions** → **Cross-origin resource sharing (CORS)**:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "HEAD"],
    "AllowedOrigins": [
      "http://localhost:3000",
      "https://your-production-domain.vercel.app"
    ],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

---

## 3. IAM user (programmatic access)

You need an **IAM user** with access keys — not your root account.

### 3a. Create policy

**IAM** → **Policies** → **Create policy** → JSON:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DentalSculptorAssets",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::dentalsculptor-assets-prod",
        "arn:aws:s3:::dentalsculptor-assets-prod/*"
      ]
    }
  ]
}
```

Name: `DentalSculptorS3Assets`

### 3b. Create user

**IAM** → **Users** → **Create user**

- Name: `dentalsculptor-app`
- Attach policy: `DentalSculptorS3Assets`
- **Create access key** → use case: **Application running outside AWS**
- Copy **Access key ID** and **Secret access key** (shown once)

---

## 4. Environment variables

Add to `dentalsculptor-app/.env` and Vercel:

```env
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=eu-west-1
AWS_S3_BUCKET=dentalsculptor-assets-prod
STORAGE_BACKEND=s3
```

Add the same four vars to **Modal secrets** (for workers):

```powershell
cd dentalsculptor-ml
python -m modal secret create dentalsculptor-aws `
  AWS_ACCESS_KEY_ID=AKIA... `
  AWS_SECRET_ACCESS_KEY=... `
  AWS_REGION=eu-west-1 `
  AWS_S3_BUCKET=dentalsculptor-assets-prod
```

Then attach in `app.py`: `secrets=[modal.Secret.from_name("dentalsculptor-aws")]`

---

## 5. Key layout

```
s3://dentalsculptor-assets-prod/
  users/{userId}/projects/{projectId}/
    source.jpg
    model.glb
    revisions/v2/edited.glb
    masks/{jobId}.png
  jobs/{jobId}/
    input.jpg
    output.glb
```

---

## 6. Verify upload (optional)

```powershell
pip install awscli
aws configure
aws s3 cp test.txt s3://dentalsculptor-assets-prod/smoke/test.txt
aws s3 ls s3://dentalsculptor-assets-prod/smoke/
```

---

## 7. Cost notes

- Storage: ~$0.023/GB/month (Standard, eu-west-1)
- PUT/GET: negligible at teaching scale
- Use **lifecycle rule** to delete `jobs/` after 30 days if desired

---

## Next code step

Wire `src/lib/storage.ts` to upload to S3 when `STORAGE_BACKEND=s3` (currently Supabase only). Modal workers upload GLB output to the same bucket; Next.js stores the returned key in Postgres.

See also: [MODAL_SETUP_GUIDE.md](./MODAL_SETUP_GUIDE.md)
