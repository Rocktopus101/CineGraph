#!/usr/bin/env bash
# Build and deploy the FastAPI backend to Google Cloud Run.
# Prerequisites: gcloud CLI, Docker, a GCP project linked to your Firebase project.
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${CLOUD_RUN_SERVICE:-cinegraph-api}"
IMAGE="gcr.io/${PROJECT_ID}/cinegraph-backend:latest"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "Set GCP_PROJECT_ID to your Firebase/GCP project id." >&2
  exit 1
fi

echo "Building backend image..."
docker build --platform linux/amd64 -t "${IMAGE}" ./backend

echo "Pushing image to GCR..."
gcloud auth configure-docker --quiet
docker push "${IMAGE}"

echo "Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --port 8000 \
  --memory 1Gi \
  --cpu 2 \
  --timeout 300 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars "DEV_MODE=false,LLM_PROVIDER=gemini" \
  --set-secrets "DATABASE_URL=cinegraph-database-url:latest,GEMINI_API_KEY=gemini-api-key:latest,TMDB_API_KEY=tmdb-api-key:latest,FIREBASE_PRIVATE_KEY=firebase-private-key:latest" \
  --project "${PROJECT_ID}"

echo "Done. Update NEXT_PUBLIC_API_URL and CORS_ORIGINS with the service URL above."
