# Supabase OAuth — Google & Microsoft

Enable SSO for DentalSculptor sign-in/sign-up. Code is already wired in `auth-form.tsx`; you only need dashboard + provider credentials.

**You do not need `gcloud` or `az` CLI** for this — use the browser steps below. CLIs are optional for automation later.

---

## Before you start — get your Supabase project ref

1. Open [supabase.com/dashboard](https://supabase.com/dashboard) → select your DentalSculptor project.
2. **Project Settings** (gear, bottom of left sidebar) → **General**.
3. Copy **Reference ID** (looks like `abcdefghijklmnop`).
4. Your OAuth callback URL is always:

```
https://<PROJECT_REF>.supabase.co/auth/v1/callback
```

Example: if ref is `xyzabc123`, callback is `https://xyzabc123.supabase.co/auth/v1/callback`.

Keep this tab open — you will paste the callback into Google and Microsoft.

---

## Step 1 — Supabase URL configuration

**Authentication → URL Configuration**

| Field | Value |
|-------|--------|
| Site URL | `https://dentalsculptor.vercel.app` |
| Redirect URLs | Add **each line separately** (not comma-separated): |

```
https://dentalsculptor.vercel.app/auth/callback
http://localhost:3000/auth/callback
https://dentalsculptor.vercel.app/consent
http://localhost:3000/consent
```

Click **Save**.

---

## Step 2 — Google OAuth

### A. Create or select a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com).
2. **Find the project picker** — top-left, next to the “Google Cloud” logo. It may say **“Select a project”** or show an existing project name.
3. Click it → in the popup click **NEW PROJECT** (top right of the dialog).
4. **Project name:** `DentalSculptor` → **Create**.
5. Wait ~30 seconds, then open the project picker again and **select DentalSculptor**.

Direct link to create a project: [console.cloud.google.com/projectcreate](https://console.cloud.google.com/projectcreate)

### B. OAuth consent screen (required once per project)

1. Left menu **☰** → **APIs & Services** → **OAuth consent screen**.
2. User type: **External** → **Create**.
3. Fill required fields only:
   - **App name:** `DentalSculptor`
   - **User support email:** your email
   - **Developer contact email:** your email
4. **Save and Continue** through Scopes and Test users (defaults are fine for pilot).
5. On **Test users**, add your own Google email if the app is still in “Testing” mode.

### C. OAuth client ID

1. **APIs & Services** → **Credentials** → **+ CREATE CREDENTIALS** → **OAuth client ID**.
2. Application type: **Web application**.
3. Name: `DentalSculptor Supabase`.
4. **Authorized JavaScript origins** — add each:

```
https://dentalsculptor.vercel.app
http://localhost:3000
https://<PROJECT_REF>.supabase.co
```

5. **Authorized redirect URIs** — add exactly:

```
https://<PROJECT_REF>.supabase.co/auth/v1/callback
```

6. **Create** → copy **Client ID** and **Client secret** (secret shown once).

Direct link (after project selected): [console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials)

### D. Enable in Supabase

1. Supabase → **Authentication** → **Providers** → **Google** → **Enable**.
2. Paste **Client ID** and **Client Secret**.
3. Confirm the **Callback URL** on that page matches what you put in Google.
4. **Save**.

---

## Step 3 — Microsoft (Azure) OAuth

Supabase uses provider id `azure` (Microsoft Entra ID / Azure AD).

### A. Open app registrations

1. Go to [portal.azure.com](https://portal.azure.com).
2. Top search bar → type **Microsoft Entra ID** → open it.
   - (Older docs say “Azure Active Directory” — same place, renamed.)
3. Left menu → **App registrations** → **+ New registration**.

Direct link: [entra.microsoft.com](https://entra.microsoft.com) → **Applications** → **App registrations**.

You do **not** need a separate “Azure subscription project” for OAuth — an app registration in Entra ID is enough.

### B. Register the app

| Field | Value |
|-------|--------|
| Name | `DentalSculptor` |
| Supported account types | **Accounts in any organizational directory and personal Microsoft accounts** |
| Redirect URI | Platform: **Web** → `https://<PROJECT_REF>.supabase.co/auth/v1/callback` |

Click **Register**.

### C. Create client secret

1. **Certificates & secrets** → **Client secrets** → **+ New client secret**.
2. Description: `supabase` → expiry: 24 months (or per your org policy).
3. **Add** → immediately copy the **Value** (not the Secret ID). You cannot see it again.

### D. Copy Application (client) ID

**Overview** page → copy **Application (client) ID** (a GUID like `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).

Optional: **Authentication** → ensure **Web** redirect URI is listed; add `http://localhost:3000` only if Microsoft requires it for testing (Supabase callback is the important one).

### E. Enable in Supabase

1. Supabase → **Authentication** → **Providers** → **Azure** → **Enable**.
2. **Client ID** = Application (client) ID (GUID like `31f606bd-6a1b-408a-b3df-7d55f12e5fc4`).
3. **Client Secret** = secret **Value** from step C — **not** the Secret ID, and **not** pasted into the Client ID field.
4. **Azure Tenant URL** — leave default for personal + work/school accounts (`common`). Use a specific tenant ID only if your university requires org-only login.
5. **Save**.

### F. Verify publisher domain (Microsoft branding)

Microsoft requires a file on your app domain before it shows **DentalSculptor** instead of an unverified publisher.

1. The repo includes:

```
dentalsculptor-app/public/.well-known/microsoft-identity-association.json
```

2. After deploy, confirm it loads:

```
https://dentalsculptor.vercel.app/.well-known/microsoft-identity-association.json
```

3. Azure → **Microsoft Entra ID** → **App registrations** → **DentalSculptor** → **Branding & properties**.
4. **Publisher domain** → enter `dentalsculptor.vercel.app` → **Verify and save domain**.

Also set on the same **Branding** page:

| Field | Value |
|-------|--------|
| Home page URL | `https://dentalsculptor.vercel.app` |
| Terms of service URL | `https://dentalsculptor.vercel.app/terms` |
| Privacy statement URL | `https://dentalsculptor.vercel.app/privacy` |
| Logo | Upload your DentalSculptor icon (240×240 PNG) |

---

## OAuth branding — show DentalSculptor, not `supabase.co`

Users see **two different places** where branding matters:

| Where | What users see today | How to fix |
|-------|----------------------|------------|
| **Google consent screen** (“Continue to …”) | Often `ozqaomjpdmdrkxthlhvx.supabase.co` | Google Cloud → **Branding** → app name + logo + publish |
| **Google sign-in summary email** | “sign in to `….supabase.co`” | Supabase **custom auth domain** (paid) **or** your own domain |
| **Microsoft login** | Unverified publisher | Publisher domain file (below) + Azure branding |
| **Your app** (sign-in page, nav) | Already DentalSculptor | No change needed |

Supabase sits in the middle of Google/Microsoft OAuth, so Google’s **email** and some **consent** text reference the Supabase project URL until you use a [custom domain for Auth](https://supabase.com/docs/guides/platform/custom-domains) (e.g. `auth.dentalsculptor.com` → Supabase). That is optional for a pilot but recommended before wider rollout.

### Google — consent screen (free, do this now)

1. [Google Cloud Console → Branding](https://console.cloud.google.com/auth/branding) (same project as your OAuth client).
2. Set **App name** to `DentalSculptor`, upload logo, support email.
3. **App domain** section:

| Field | Value |
|-------|--------|
| Application home page | `https://dentalsculptor.vercel.app` |
| Privacy policy | `https://dentalsculptor.vercel.app/privacy` |
| Terms of service | `https://dentalsculptor.vercel.app/terms` |

4. **Authorized domains:** `dentalsculptor.vercel.app` only — **never** add `supabase.co`.
5. Verify site in [Search Console](https://search.google.com/search-console) (HTML tag → `GOOGLE_SITE_VERIFICATION` on Vercel — already wired in the app).
6. **Publish app** (OAuth consent screen → move from Testing to **In production**).

After publish, the live consent screen should say **DentalSculptor** with your logo. Google’s post-login email may still mention `supabase.co` until you add a Supabase custom auth domain.

### Microsoft — publisher domain (free, do this now)

See **Step 3F** above. Host `microsoft-identity-association.json` on Vercel, then verify `dentalsculptor.vercel.app` in Azure **Branding & properties**.

### Supabase — emails and “who am I signing into?”

1. **Authentication → URL Configuration** — Site URL must be `https://dentalsculptor.vercel.app` (not the Supabase URL).
2. **Authentication → Email templates** — edit **Confirm signup**, **Magic link**, etc. Replace generic copy with “DentalSculptor” and link to your app URL.
3. **Optional (best long-term):** Supabase **Settings → Custom domains** → e.g. `auth.yourdomain.com` — update Google/Azure callback URLs to include the custom domain callback. This removes `supabase.co` from OAuth emails and consent text.

### Dashboard after sign-in (not from 3D generation)

Normal path: **Sign in → Consent → Onboarding → Dashboard**.

The **editor resume** path (`/auth/continue`) only runs when you generated a 3D model on the landing page first. If you sign in directly, onboarding sends you to **Dashboard** — not the editor.

If Dashboard errors after OAuth, it is usually an account linking issue (Clerk-era email vs new Supabase ID). The app now links by email automatically on deploy.

---

## Step 4 — Optional pilot settings

**Authentication → Providers → Email** → turn off **Confirm email** for faster supervisor testing.

---

## Step 5 — Test

1. Local: `npm run dev` in `dentalsculptor-app` → http://localhost:3000/sign-in
2. Click **Continue with Google** and **Continue with Microsoft**.
3. Expect: provider login → redirect to `/auth/callback` → `/consent`.
4. Production: incognito → https://dentalsculptor.vercel.app/sign-in

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `redirect_uri_mismatch` | Callback in Google/Azure must **exactly** match Supabase (`/auth/v1/callback`) |
| Google “Access blocked: app not verified” | Add your email under OAuth consent screen → **Test users**, or publish app (not needed for pilot) |
| Microsoft “AADSTS50011” redirect mismatch | Re-check Web redirect URI in Entra app registration |
| Provider not enabled | Toggle Google/Azure on in Supabase Providers |
| Stuck after login | Check Vercel `DATABASE_URL` and Supabase redirect URLs include `/auth/callback` |

---

## Checklist

- [ ] Supabase project ref copied
- [ ] Supabase URL Configuration saved
- [ ] Google Cloud project **DentalSculptor** created and selected
- [ ] Google OAuth consent screen configured
- [ ] Google OAuth client created with Supabase callback
- [ ] Google enabled in Supabase Providers
- [ ] Microsoft Entra app **DentalSculptor** registered
- [ ] Microsoft client secret saved
- [ ] Azure enabled in Supabase Providers
- [ ] Sign-in tested locally and on Vercel

---

## Google Search Console (only if verifying branding / production)

### Why `*.vercel.app` is painful

| Property type | Where to type URL | Verification options | Works on Vercel subdomain? |
|---------------|-------------------|----------------------|----------------------------|
| **Domain** (left) | `dentalsculptor.vercel.app` — **no** `https://` | DNS TXT **only** | **No** — you do not control `vercel.app` DNS |
| **URL prefix** (right) | `https://dentalsculptor.vercel.app` — **with** `https://` | HTML tag, HTML file, etc. | **Yes** — if Continue works in your browser |

**Common mistake (see screenshot):** typing `https://dentalsculptor.vercel.app` in the **left** Domain box shows *“Remove protocols and paths”* and only leads to TXT — that path cannot succeed on Vercel.

**URL prefix steps (try once more in Chrome incognito):**

1. Click the **right** card (**URL prefix**), not Domain.
2. Enter exactly: `https://dentalsculptor.vercel.app`
3. **Continue** → choose **HTML file** (easiest — no Vercel env var).
4. Send the downloaded filename + contents to add under `dentalsculptor-app/public/`, deploy, then Verify.

If URL prefix Continue is blank or broken in your browser, skip to **custom domain** below — that is the reliable fix.

### Recommended: custom domain + DNS TXT (Route 53 or any registrar)

Google OAuth branding verification is much easier when you **own** the domain:

1. Register e.g. `dentalsculptor.com` (Route 53, Cloudflare, Namecheap — check whether AWS credits cover registration).
2. **Vercel** → Project → **Settings → Domains** → add the domain → follow DNS instructions.
3. Update **Supabase** Site URL + redirect URLs to the new domain.
4. Update **Google OAuth** home page, privacy, terms, and client origins/redirects.
5. **Search Console** → **Domain** (left) → enter `dentalsculptor.com` (no `https://`) → add Google’s **TXT** record at your DNS host → Verify.
6. Retry OAuth **branding re-verification**.

This matches how Google expects production apps to work and avoids Vercel subdomain verification quirks.

### HTML tag on Vercel (if URL prefix works)

**Do not use DNS TXT** for `dentalsculptor.vercel.app` — you do not control `vercel.app` DNS.

1. [search.google.com/search-console](https://search.google.com/search-console) → **Add property** → **URL prefix** → `https://dentalsculptor.vercel.app`
2. Verification method: **HTML tag** (not Domain / DNS TXT)
3. Copy the `content="..."` value from the meta tag Google shows
4. Set in Vercel env: `GOOGLE_SITE_VERIFICATION=<that value>` (also in local `.env`)
5. Redeploy Vercel → Search Console → **Verify**
6. Then retry OAuth consent screen re-verification if needed

For a **Testing** OAuth app with test users only, Search Console verification is **not required**.

---

## Publish Google OAuth for all users (beyond supervisor pilot)

Google **Test users** and your **app invite link** are separate:

| Gate | What it controls | How to open up |
|------|------------------|----------------|
| Google **Testing** mode | Who can click “Continue with Google” | **Publish** OAuth app to Production |
| Your **`?invite=`** link | Anonymous generation on landing | Share invite URL (already works) |
| **Sign-in** (Supabase) | Full app after OAuth | Any user once Google is Production |

To let **any invited educator** sign in with Google **without** adding their email in Google Cloud:

### 1. Complete OAuth consent screen

| Field | Value |
|-------|--------|
| Home page | `https://dentalsculptor.vercel.app` |
| Privacy policy | `https://dentalsculptor.vercel.app/privacy` |
| Terms of service | `https://dentalsculptor.vercel.app/terms` |
| Authorized domains | `dentalsculptor.vercel.app` only (domains you own — **not** `supabase.co`) |

**Important:** Do **not** add `supabase.co` to **Authorized domains** on the consent screen — Google rejects it (“must be a top private domain”) because you do not own Supabase. Put your Supabase callback URL only under **Credentials → OAuth client → Authorized redirect URIs** (see step 2C above).

### 2. Verify site ownership (Search Console)

URL prefix → `https://dentalsculptor.vercel.app` → **HTML tag** → set `GOOGLE_SITE_VERIFICATION` on Vercel → redeploy → Verify.

### 3. Publish the app

Google Cloud → **OAuth consent screen** → **Publish app** (move from Testing to **In production**).

Google may require a **verification review** (days to weeks). Basic sign-in scopes (email, profile) usually pass once privacy/terms and domain verification are in place.

### 4. Microsoft

Azure app registrations with **personal + work/school accounts** typically allow any Microsoft user **without** a Google-style test-user list. Ensure Supabase Azure provider is enabled.

### 5. Interim: email/password

Supabase **Email** provider works for any user without Google Test users — useful while Google review is pending.

### Your invite model stays the same

- Share: `https://dentalsculptor.vercel.app/?invite=YOUR_CODE`
- Invite gates **landing generation** for anonymous users
- After sign-in, users go through **consent → onboarding** as today
- You do **not** need per-user Google test entries once the app is **In production**

---

## Optional: install CLIs later (not required)

If you want CLI access for other work:

```powershell
# Google Cloud SDK
winget install Google.CloudSDK

# Azure CLI
winget install Microsoft.AzureCLI
```

Then: `gcloud auth login` and `az login`. OAuth client setup is still easiest in the browser for a one-time setup.
