#!/bin/bash
# Run this ONCE to create all secrets in Google Secret Manager.
# Usage: ./setup_secrets.sh YOUR_PROJECT_ID

set -e

PROJECT_ID=${1:-$(gcloud config get-value project)}

if [ -z "$PROJECT_ID" ]; then
  echo "ERROR: No project ID. Run: ./setup_secrets.sh YOUR_PROJECT_ID"
  exit 1
fi

echo "Creating secrets in project: $PROJECT_ID"

create_secret() {
  local name=$1
  local value=$2

  if gcloud secrets describe "$name" --project="$PROJECT_ID" &>/dev/null; then
    echo "  [UPDATE] $name"
    echo -n "$value" | gcloud secrets versions add "$name" \
      --data-file=- --project="$PROJECT_ID"
  else
    echo "  [CREATE] $name"
    echo -n "$value" | gcloud secrets create "$name" \
      --data-file=- --project="$PROJECT_ID" \
      --replication-policy=automatic
  fi
}

# --- Secrets (sensitive values only) ---
create_secret "GOOGLE_API_KEY"            "YOUR_GOOGLE_API_KEY"
create_secret "OPENROUTER_API_KEY"        "YOUR_OPENROUTER_API_KEY"
create_secret "SUPABASE_URL"             "YOUR_SUPABASE_URL"
create_secret "SUPABASE_PUBLISHABLE_KEY" "YOUR_SUPABASE_PUBLISHABLE_KEY"
create_secret "SUPABASE_SECRET_KEY"      "YOUR_SUPABASE_SECRET_KEY"

echo ""
echo "Done. Grant Cloud Run access with:"
echo "  gcloud projects add-iam-policy-binding $PROJECT_ID \\"
echo "    --member='serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com' \\"
echo "    --role='roles/secretmanager.secretAccessor'"
