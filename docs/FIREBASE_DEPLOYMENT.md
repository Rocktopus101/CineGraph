# Firebase Deployment Guide

CineGraph uses **Firebase Auth** for users, a hosted **Next.js frontend**, and a hosted **FastAPI backend**. PostgreSQL with **pgvector** stores movies, embeddings, and user data.

## Choose a deployment path

| | **Path B — no Cloud SQL** (recommended if avoiding GCP DB billing) | **Path A — all GCP** |
|---|---|---|
| Database | [Neon](https://neon.tech) or [Supabase](https://supabase.com) free tier | Cloud SQL (~$10–30/mo) |
| Backend | [Render](https://render.com) free tier | Cloud Run |
| Frontend | Vercel free tier **or** Firebase App Hosting | Firebase App Hosting |
| Firebase Auth | Steps 1–4 below (same) | Steps 1–4 below (same) |
| GCP billing | Not required for DB; App Hosting still needs Blaze if you use it | Blaze plan for Run + App Hosting |

> **You've completed steps 1–4.** Continue with **Path B, step 5** below to skip Cloud SQL entirely.

### Path B architecture (no Cloud SQL)

```
Browser
  │
  ├─ Firebase Auth (sign-in / ID tokens)          ← Spark plan, free
  │
  ├─ Vercel or Firebase App Hosting ──► Next.js
  │         │
  │         └── NEXT_PUBLIC_API_URL ──► Render (FastAPI)
  │                                        │
  │                                        ├── Firebase Admin SDK (verify tokens)
  │                                        └── Neon / Supabase PostgreSQL + pgvector
```

### Path A architecture (all GCP)

```
Browser
  │
  ├─ Firebase Auth (sign-in / ID tokens)
  │
  ├─ Firebase App Hosting ──► Next.js frontend
  │         │
  │         └── NEXT_PUBLIC_API_URL ──► Cloud Run (FastAPI)
  │                                        │
  │                                        ├── Firebase Admin SDK (verify tokens)
  │                                        └── Cloud SQL PostgreSQL + pgvector
```

## 1. Create a Firebase project

1. Go to [Firebase Console](https://console.firebase.google.com/) → **Add project**.
2. Enable **Google Analytics** (optional).
3. Note your **Project ID** — you'll use it everywhere.

Link the project to GCP (automatic for new Firebase projects).

## 2. Enable Firebase Authentication

1. Firebase Console → **Build** → **Authentication** → **Get started**.
2. **Sign-in method** → enable **Email/Password**.
3. (Optional) Add authorized domains under **Settings** → **Authorized domains**:
   - `localhost` (dev)
   - Your App Hosting domain (e.g. `your-app--your-project.us-central1.hosted.app`)
   - Your custom domain if you add one

## 3. Register the web app (frontend SDK config)

1. Firebase Console → **Project settings** → **General** → **Your apps** → **Add app** → **Web**.
2. Copy the `firebaseConfig` values into your env:

```env
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=...
NEXT_PUBLIC_FIREBASE_APP_ID=...
```

## 4. Create a service account (backend Admin SDK)

1. Firebase Console → **Project settings** → **Service accounts**.
2. Click **Generate new private key** → download JSON.
3. Extract these values for the backend:

```env
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@your-project.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
```

> Keep the JSON file secure. Never commit it to git.

---

## Path B (recommended): Neon database — no GCP billing

### 5B. Create a Neon PostgreSQL database

1. Sign up at [neon.tech](https://neon.tech) (free tier — no credit card for basic usage).
2. **New project** → pick a region close to your backend (e.g. `us-east-2`).
3. Copy the connection string from the dashboard (Neon format is fine):

```
postgresql://USER:PASSWORD@ep-xxxx.region.aws.neon.tech/neondb?sslmode=require
```

CineGraph auto-converts this to `postgresql+asyncpg://...?ssl=require` at runtime.

4. Open **SQL Editor** in Neon and run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

5. Run Alembic migrations against Neon (from your machine or after backend is deployed):

```bash
cd backend
DATABASE_URL="postgresql+asyncpg://USER:PASSWORD@ep-xxxx.region.aws.neon.tech/neondb?ssl=require" \
  alembic upgrade head
```

6. (Optional) Seed sample data:

```bash
DATABASE_URL="postgresql+asyncpg://..." python ../scripts/seed.py
```

### 5B-alt. Supabase instead of Neon

1. [supabase.com](https://supabase.com) → **New project** (free tier).
2. **Project Settings → Database** → copy the **Connection string** (URI).
3. Use the **Transaction pooler** URL (port `6543`) for serverless backends.
4. Convert to asyncpg format:

```
postgresql+asyncpg://postgres.PROJECT:PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres?ssl=require
```

5. In **SQL Editor**, run `CREATE EXTENSION IF NOT EXISTS vector;` (enabled by default on most projects).
6. Run `alembic upgrade head` as above.

### 6B. Deploy the backend to Render (free tier)

1. Push your repo to GitHub (already done if you followed earlier steps).
2. Go to [render.com](https://render.com) → **New → Blueprint** → connect `Rocktopus101/CineGraph`.
3. Render reads `render.yaml` at the repo root. Or create a **Web Service** manually:
   - **Root directory**: leave blank (uses `backend/` via Dockerfile path in blueprint)
   - **Environment**: Docker
   - **Dockerfile path**: `backend/Dockerfile`
4. Set environment variables in the Render dashboard:

```env
DATABASE_URL=postgresql://...@ep-xxxx.neon.tech/neondb?sslmode=require
DEV_MODE=false
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key
TMDB_API_KEY=your-key
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CLIENT_EMAIL=firebase-adminsdk@...
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
CORS_ORIGINS=https://your-frontend.vercel.app
```

> For `FIREBASE_PRIVATE_KEY` on Render, paste the key with real newlines or use `\n` escapes.

5. Deploy. Note your Render URL (e.g. `https://cinegraph-api.onrender.com`).
6. Free-tier Render services spin down after inactivity — first request after idle may take 30–60s.

### 7B. Deploy the frontend

**Option 1 — Vercel (free, no Firebase Blaze required)**

1. [vercel.com](https://vercel.com) → **Import** your GitHub repo.
2. Set **Root Directory** to `frontend`.
3. Add environment variables:

```env
NEXT_PUBLIC_API_URL=https://cinegraph-api.onrender.com
NEXT_PUBLIC_DEV_MODE=false
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=...
NEXT_PUBLIC_FIREBASE_APP_ID=...
```

4. Deploy. Add your Vercel URL to Firebase **Authorized domains** (Authentication → Settings).
5. Update backend `CORS_ORIGINS` on Render to include the Vercel URL.

**Option 2 — Firebase App Hosting**

Same as [step 7](#7-deploy-the-frontend-with-firebase-app-hosting) below, but set `NEXT_PUBLIC_API_URL` to your Render URL. Requires upgrading Firebase to the **Blaze** plan (pay-as-you-go; can stay at $0 on low traffic).

### 8B. Verify (Path B)

1. Open your Vercel or App Hosting URL.
2. Sign in with Firebase Auth.
3. Import Letterboxd data via **Settings** (embedding step may take several minutes on Gemini free tier).
4. Test **AI Recommendations**.

---

## Path A: Cloud SQL + Cloud Run (GCP)

## 5. Set up Cloud SQL (PostgreSQL + pgvector)

1. [GCP Console](https://console.cloud.google.com/) → **SQL** → **Create instance** → **PostgreSQL 16**.
2. After creation, connect and enable pgvector:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

3. Create database and user:

```sql
CREATE DATABASE cinegraph;
CREATE USER cinegraph WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE cinegraph TO cinegraph;
```

4. Build the async connection string for Cloud Run (use Cloud SQL Auth Proxy or private IP):

```
postgresql+asyncpg://cinegraph:PASSWORD@/cinegraph?host=/cloudsql/PROJECT:REGION:INSTANCE
```

Store as a Secret Manager secret: `cinegraph-database-url`.

## 6. Deploy the backend to Cloud Run

### One-time GCP setup

```bash
# Install gcloud CLI: https://cloud.google.com/sdk/docs/install
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com containerregistry.googleapis.com secretmanager.googleapis.com sqladmin.googleapis.com

# Store secrets (repeat for each key)
echo -n "postgresql+asyncpg://..." | gcloud secrets create cinegraph-database-url --data-file=-
echo -n "your-gemini-key" | gcloud secrets create gemini-api-key --data-file=-
echo -n "your-tmdb-key" | gcloud secrets create tmdb-api-key --data-file=-
echo -n "firebase-adminsdk@..." | gcloud secrets create firebase-client-email --data-file=-
# For private key, use a file:
gcloud secrets create firebase-private-key --data-file=./firebase-service-account.pem
```

### Deploy

```bash
chmod +x scripts/deploy-backend.sh
GCP_PROJECT_ID=your-project-id ./scripts/deploy-backend.sh
```

After deploy, note the Cloud Run URL (e.g. `https://cinegraph-api-xxxxx-uc.a.run.app`).

### Production backend env

```env
DEV_MODE=false
CORS_ORIGINS=https://your-app--your-project.us-central1.hosted.app,https://your-project.web.app
DATABASE_URL=<from Secret Manager>
GEMINI_API_KEY=<from Secret Manager>
TMDB_API_KEY=<from Secret Manager>
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CLIENT_EMAIL=<from Secret Manager>
FIREBASE_PRIVATE_KEY=<from Secret Manager>
```

Set `CORS_ORIGINS` to match your deployed frontend URL(s).

## 7. Deploy the frontend with Firebase App Hosting

### Install Firebase CLI

```bash
npm install -g firebase-tools
firebase login
```

### Link project

```bash
cp .firebaserc.example .firebaserc
# Edit .firebaserc with your project id
```

### Configure App Hosting

1. Edit `apphosting.yaml`:
   - Set `NEXT_PUBLIC_API_URL` to your Cloud Run URL.
   - Set Firebase client config values.
   - Set `NEXT_PUBLIC_DEV_MODE` to `"false"`.

2. Store sensitive values in Firebase Secret Manager (Console → App Hosting → Secrets):
   - `FIREBASE_API_KEY`
   - `FIREBASE_MESSAGING_SENDER_ID`
   - `FIREBASE_APP_ID`

### Deploy via Console (recommended first time)

1. Firebase Console → **Build** → **App Hosting** → **Get started**.
2. Connect your GitHub repo.
3. Set **Root directory** to `frontend`.
4. App Hosting detects Next.js and uses `apphosting.yaml` at the repo root.
5. Deploy.

### Deploy via CLI

```bash
firebase apphosting:backends:create --project your-project-id
firebase deploy --only apphosting
```

## 8. Verify end-to-end

1. Open your App Hosting URL.
2. Click **Sign in** → create an account.
3. Import Letterboxd data via **Settings**.
4. Open **AI Recommendations** and send a chat message.
5. Check Cloud Run logs if requests fail:

```bash
gcloud run services logs read cinegraph-api --region us-central1
```

## Local development with real Firebase Auth

To test Firebase auth locally while still using Docker:

```env
# .env
DEV_MODE=false
NEXT_PUBLIC_DEV_MODE=false

# Backend — Firebase Admin SDK
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CLIENT_EMAIL=...
FIREBASE_PRIVATE_KEY="..."

# Frontend — Firebase client SDK
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=...
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=...
NEXT_PUBLIC_FIREBASE_APP_ID=...

NEXT_PUBLIC_API_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Restart containers:

```bash
docker compose down && docker compose up --build
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `401 Not authenticated` | Ensure frontend sends `Authorization: Bearer <idToken>`. Check `DEV_MODE=false` on backend. |
| CORS errors | Add your frontend URL to `CORS_ORIGINS` on the backend. |
| `Firebase not configured` on login | Set all `NEXT_PUBLIC_FIREBASE_*` vars and `NEXT_PUBLIC_DEV_MODE=false`. |
| Backend can't verify tokens | Check `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY`. |
| Import hangs on embeddings | Normal on Gemini free tier; consider raising Cloud Run timeout to 300s. |

## Cost notes

| Service | Path B (Neon + Render + Vercel) | Path A (GCP) |
|---------|----------------------------------|--------------|
| Firebase Auth | Free (Spark plan) | Free (Spark plan) |
| Database | Neon/Supabase free tier | Cloud SQL ~$10–30/mo |
| Backend | Render free tier (cold starts) | Cloud Run free tier with Blaze |
| Frontend | Vercel free tier | App Hosting (Blaze) |
| Gemini / TMDB | Your API keys | Your API keys |

**Path B** keeps you off Cloud SQL billing entirely. The main trade-offs are Render cold starts on the free tier and running migrations manually against Neon before first deploy.
