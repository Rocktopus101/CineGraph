# Firebase Deployment Guide

CineGraph uses **Firebase Auth** for users, **Firebase App Hosting** for the Next.js frontend, and **Google Cloud Run** for the FastAPI backend. PostgreSQL runs on **Cloud SQL** (with pgvector).

## Architecture

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

- **Firebase Auth**: free tier covers most small apps.
- **App Hosting**: pay per use; `minInstances: 0` in `apphosting.yaml` keeps idle cost low.
- **Cloud Run**: scales to zero; cold starts add ~2–5s latency.
- **Cloud SQL**: smallest instance is the main fixed cost (~$10–30/mo).
