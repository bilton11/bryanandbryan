#!/usr/bin/env bash
# =============================================================================
# Bryan and Bryan — GCP Infrastructure Setup
# =============================================================================
# Run this in Google Cloud Shell (https://shell.cloud.google.com)
# It creates everything needed for the GitHub Actions deploy to work.
#
# BEFORE RUNNING: Set the variables below.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# ⚠️  EDIT THESE BEFORE RUNNING
# ---------------------------------------------------------------------------
PROJECT_ID="your-gcp-project-id"        # e.g. "bryanandbryan-prod"
BILLING_ACCOUNT=""                        # e.g. "01ABCD-234EFG-567HIJ" (run: gcloud billing accounts list)
GITHUB_REPO="bilton11/bryanandbryan"      # GitHub owner/repo
DB_PASSWORD="CHANGE_ME_TO_SOMETHING_STRONG"
FLASK_SECRET_KEY="$(openssl rand -hex 32)"
ANTHROPIC_API_KEY=""                      # Your Anthropic API key
MAIL_USERNAME=""                          # Gmail address for sending magic links
MAIL_PASSWORD=""                          # Gmail App Password (NOT your Gmail password — see instructions)
# ---------------------------------------------------------------------------

REGION="northamerica-northeast1"          # Montreal — Canadian data residency
SQL_INSTANCE="bb-postgres"
SQL_DB="bryanandbryan"
SQL_USER="bb-app"
SERVICE="bryanandbryan"
REPO_NAME="app"
SA_NAME="bb-cloudrun"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
WIF_POOL="github-pool"
WIF_PROVIDER="github-provider"

echo "============================================"
echo "Setting up GCP for Bryan and Bryan"
echo "Project: $PROJECT_ID"
echo "Region:  $REGION"
echo "============================================"

# --- 1. Create project (skip if it already exists) ---
echo ""
echo ">>> Step 1: Create/select project"
gcloud projects create "$PROJECT_ID" --name="Bryan and Bryan" 2>/dev/null || true
gcloud config set project "$PROJECT_ID"

# --- 2. Link billing ---
echo ""
echo ">>> Step 2: Link billing account"
if [ -n "$BILLING_ACCOUNT" ]; then
  gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT"
else
  echo "⚠️  No BILLING_ACCOUNT set — link billing manually in GCP Console"
  echo "   https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
  read -p "Press Enter after billing is linked..."
fi

# --- 3. Enable APIs ---
echo ""
echo ">>> Step 3: Enable required APIs"
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  cloudresourcemanager.googleapis.com \
  compute.googleapis.com

echo "APIs enabled."

# --- 4. Create Artifact Registry repo ---
echo ""
echo ">>> Step 4: Create Artifact Registry Docker repo"
gcloud artifacts repositories create "$REPO_NAME" \
  --repository-format=docker \
  --location="$REGION" \
  --description="Bryan and Bryan container images" \
  2>/dev/null || echo "  (repo already exists)"

# --- 5. Create Cloud SQL instance ---
echo ""
echo ">>> Step 5: Create Cloud SQL PostgreSQL instance"
echo "  This takes 5-10 minutes..."
gcloud sql instances create "$SQL_INSTANCE" \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region="$REGION" \
  --storage-size=10GB \
  --storage-auto-increase \
  --availability-type=zonal \
  --assign-ip \
  2>/dev/null || echo "  (instance already exists)"

echo "  Creating database..."
gcloud sql databases create "$SQL_DB" \
  --instance="$SQL_INSTANCE" \
  2>/dev/null || echo "  (database already exists)"

echo "  Creating user..."
gcloud sql users create "$SQL_USER" \
  --instance="$SQL_INSTANCE" \
  --password="$DB_PASSWORD" \
  2>/dev/null || echo "  (user already exists)"

# --- 6. Create Secret Manager secrets ---
echo ""
echo ">>> Step 6: Create secrets in Secret Manager"

create_secret() {
  local name="$1"
  local value="$2"
  gcloud secrets create "$name" 2>/dev/null || true
  echo -n "$value" | gcloud secrets versions add "$name" --data-file=-
  echo "  ✓ $name"
}

create_secret "bb-secret-key"       "$FLASK_SECRET_KEY"
create_secret "bb-db-password"      "$DB_PASSWORD"
create_secret "bb-anthropic-api-key" "$ANTHROPIC_API_KEY"
create_secret "bb-mail-username"    "$MAIL_USERNAME"
create_secret "bb-mail-password"    "$MAIL_PASSWORD"

# --- 7. Create service account for Cloud Run ---
echo ""
echo ">>> Step 7: Create Cloud Run service account"
gcloud iam service-accounts create "$SA_NAME" \
  --display-name="Bryan and Bryan Cloud Run" \
  2>/dev/null || echo "  (service account already exists)"

# Grant roles to the service account
echo "  Granting roles..."
for role in \
  roles/cloudsql.client \
  roles/secretmanager.secretAccessor \
  roles/run.invoker; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="$role" \
    --quiet
done
echo "  ✓ Roles granted"

# --- 8. Set up Workload Identity Federation ---
echo ""
echo ">>> Step 8: Set up Workload Identity Federation (WIF)"

# Create the pool
gcloud iam workload-identity-pools create "$WIF_POOL" \
  --location="global" \
  --display-name="GitHub Actions" \
  2>/dev/null || echo "  (pool already exists)"

# Create the provider
gcloud iam workload-identity-pools providers create-oidc "$WIF_PROVIDER" \
  --location="global" \
  --workload-identity-pool="$WIF_POOL" \
  --display-name="GitHub" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  2>/dev/null || echo "  (provider already exists)"

# Get the pool ID
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
WIF_PROVIDER_FULL="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${WIF_POOL}/providers/${WIF_PROVIDER}"

# Allow GitHub repo to impersonate the service account
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${WIF_POOL}/attribute.repository/${GITHUB_REPO}" \
  --quiet

echo "  ✓ WIF configured"

# --- 9. Grant GitHub Actions SA permissions to push images and deploy ---
echo ""
echo ">>> Step 9: Grant deploy permissions"

# Artifact Registry writer (push Docker images)
gcloud artifacts repositories add-iam-policy-binding "$REPO_NAME" \
  --location="$REGION" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/artifactregistry.writer" \
  --quiet

# Cloud Run admin (deploy services)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.admin" \
  --quiet

# Allow SA to act as itself (required for Cloud Run deploy)
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --role="roles/iam.serviceAccountUser" \
  --member="serviceAccount:${SA_EMAIL}" \
  --quiet

echo "  ✓ Deploy permissions granted"

# --- 10. Print GitHub secrets to configure ---
echo ""
echo "============================================"
echo "✓ GCP SETUP COMPLETE"
echo "============================================"
echo ""
echo "Now add these 3 secrets to your GitHub repo:"
echo "  https://github.com/${GITHUB_REPO}/settings/secrets/actions"
echo ""
echo "  GCP_PROJECT_ID     = ${PROJECT_ID}"
echo "  WIF_PROVIDER       = ${WIF_PROVIDER_FULL}"
echo "  WIF_SERVICE_ACCOUNT = ${SA_EMAIL}"
echo ""
echo "Then push a commit to main and the deploy should succeed."
echo ""
echo "Your Cloud Run URL will be:"
echo "  https://${SERVICE}-*.run.app"
echo "  (exact URL shown after first successful deploy)"
echo "============================================"
