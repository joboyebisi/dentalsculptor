# Supabase OAuth — Google & Microsoft

Enable SSO for DentalSculptor sign-in/sign-up. Code is already wired in `auth-form.tsx`; you only need dashboard + provider credentials.

---

## 1. Supabase URL configuration

**Authentication → URL Configuration**

| Field | Value |
|-------|--------|
| Site URL | `https://dentalsculptor.vercel.app` |
| Redirect URLs | Add each separately: |

```
https://dentalsculptor.vercel.app/auth/callback
http://localhost:3000/auth/callback
https://dentalsculptor.vercel.app/consent
http://localhost:3000/consent
```

---

## 2. Google

### Google Cloud Console

1. [console.cloud.google.com](https://console.cloud.google.com) → create or select project
2. **APIs & Services → OAuth consent screen** → External → add app name, support email
3. **Credentials → Create credentials → OAuth client ID → Web application**
4. **Authorized JavaScript origins:**
   - `https://dentalsculptor.vercel.app`
   - `http://localhost:3000`
   - `https://<YOUR_PROJECT_REF>.supabase.co`
5. **Authorized redirect URIs** (copy from Supabase — step below):
   - `https://<YOUR_PROJECT_REF>.supabase.co/auth/v1/callback`

### Supabase

1. **Authentication → Providers → Google → Enable**
2. Paste **Client ID** and **Client Secret** from Google
3. Copy the **Callback URL** shown on that page into Google redirect URIs if not already added

---

## 3. Microsoft (Azure)

### Azure Portal

1. [portal.azure.com](https://portal.azure.com) → **Microsoft Entra ID → App registrations → New registration**
2. Name: `DentalSculptor`
3. Supported account types: **Accounts in any organizational directory and personal Microsoft accounts**
4. Redirect URI: **Web** → `https://<YOUR_PROJECT_REF>.supabase.co/auth/v1/callback`
5. After create: **Certificates & secrets → New client secret** (save value)
6. **Overview** → copy **Application (client) ID**

### Supabase

1. **Authentication → Providers → Azure → Enable**
2. Paste **Application (client) ID** as Client ID
3. Paste **Client secret**
4. Azure URL: leave default or use your tenant if org-only

---

## 4. Test

1. Local: `npm run dev` → `/sign-in` → **Continue with Google** / **Microsoft**
2. Production: incognito → https://dentalsculptor.vercel.app/sign-in
3. Expect redirect → `/auth/callback` → `/consent`

### Common errors

| Error | Fix |
|-------|-----|
| redirect_uri_mismatch | Add exact Supabase callback URL to Google/Azure |
| Provider not enabled | Toggle on in Supabase Providers |
| Stuck on consent | Check `DATABASE_URL` on Vercel (Prisma user sync) |

---

## 5. Optional: disable email confirmation (pilot)

**Authentication → Providers → Email** → turn off **Confirm email** for faster supervisor testing.
