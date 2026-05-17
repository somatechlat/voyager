#!/usr/bin/env bash
# =============================================================================
# VOYAGER - Vault Initialization Script
# =============================================================================
# Automatically initializes HashiCorp Vault for Voyager:
#   - Enables KV v2 secrets engine at path "voyager"
#   - Creates secret paths for all Voyager services
#   - Creates read/write policies
#   - Generates AppRole for voyager-api authentication
#
# Usage:
#   ./vault-init.sh [VAULT_ADDR] [VAULT_TOKEN]
#
# Environment:
#   VAULT_ADDR  - Vault server URL (default: http://localhost:8200)
#   VAULT_TOKEN - Vault root token (default: dev-root-token)
# =============================================================================

set -euo pipefail

VAULT_ADDR="${1:-${VAULT_ADDR:-http://localhost:8200}}"
VAULT_TOKEN="${2:-${VAULT_TOKEN:-dev-root-token}}"
VOYAGER_PATH="${VOYAGER_VAULT_PATH:-voyager}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# Check dependencies
for cmd in curl jq; do
    if ! command -v "$cmd" &>/dev/null; then
        log_error "$cmd is required but not installed"
        exit 1
    fi
done

# Wait for Vault to be ready
log_info "Waiting for Vault at $VAULT_ADDR..."
for i in {1..30}; do
    if curl -sf "$VAULT_ADDR/v1/sys/health" &>/dev/null; then
        log_ok "Vault is healthy"
        break
    fi
    if [ "$i" -eq 30 ]; then
        log_error "Vault did not become healthy within 60 seconds"
        exit 1
    fi
    sleep 2
done

# Set Vault token header
AUTH_HEADER="X-Vault-Token: $VAULT_TOKEN"

# =============================================================================
# STEP 1: Enable KV v2 secrets engine
# =============================================================================
log_info "Step 1: Enabling KV v2 secrets engine at path '$VOYAGER_PATH'..."

# Check if mount already exists
EXISTING_MOUNT=$(curl -sf -H "$AUTH_HEADER" "$VAULT_ADDR/v1/sys/mounts" | jq -r ".data.\"$VOYAGER_PATH/\" // empty")

if [ -n "$EXISTING_MOUNT" ]; then
    log_warn "Secrets engine '$VOYAGER_PATH' already mounted, skipping"
else
    curl -sf -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" \
        -d '{
            "type": "kv",
            "options": {"version": "2"},
            "description": "Voyager application secrets"
        }' \
        "$VAULT_ADDR/v1/sys/mounts/$VOYAGER_PATH" >/dev/null
    log_ok "KV v2 secrets engine enabled at '$VOYAGER_PATH'"
fi

# =============================================================================
# STEP 2: Create secret paths
# =============================================================================
log_info "Step 2: Creating secret paths..."

# Django core secrets
curl -sf -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" \
    -d '{
        "data": {
            "SECRET_KEY": "replace-with-50-char-secret-key-for-django",
            "DATABASE_URL": "replace-with-production-database-url",
            "DEBUG": "false",
            "ALLOWED_HOSTS": "*",
            "LOG_LEVEL": "INFO"
        }
    }' \
    "$VAULT_ADDR/v1/$VOYAGER_PATH/data/django/config" >/dev/null
log_ok "Created secret: voyager/django/config"

# Database credentials
curl -sf -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" \
    -d '{
        "data": {
            "host": "voyager_postgres",
            "port": "5432",
            "database": "voyager",
            "username": "voyager",
            "password": "replace-with-secure-password",
            "ssl_mode": "require"
        }
    }' \
    "$VAULT_ADDR/v1/$VOYAGER_PATH/data/database/credentials" >/dev/null
log_ok "Created secret: voyager/database/credentials"

# Platform API keys (marketing platforms)
curl -sf -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" \
    -d '{
        "data": {
            "FACEBOOK_APP_ID": "",
            "FACEBOOK_APP_SECRET": "",
            "FACEBOOK_ACCESS_TOKEN": "",
            "GOOGLE_ADS_DEVELOPER_TOKEN": "",
            "GOOGLE_ADS_CLIENT_ID": "",
            "GOOGLE_ADS_CLIENT_SECRET": "",
            "GOOGLE_ADS_REFRESH_TOKEN": "",
            "LINKEDIN_CLIENT_ID": "",
            "LINKEDIN_CLIENT_SECRET": "",
            "TWITTER_API_KEY": "",
            "TWITTER_API_SECRET": "",
            "TIKTOK_ACCESS_TOKEN": "",
            "REDDIT_CLIENT_ID": "",
            "REDDIT_CLIENT_SECRET": "",
            "YOUTUBE_API_KEY": ""
        }
    }' \
    "$VAULT_ADDR/v1/$VOYAGER_PATH/data/platforms/api-keys" >/dev/null
log_ok "Created secret: voyager/platforms/api-keys"

# AI / LLM provider keys
curl -sf -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" \
    -d '{
        "data": {
            "OPENAI_API_KEY": "",
            "OPENAI_ORG_ID": "",
            "ANTHROPIC_API_KEY": "",
            "HUGGINGFACE_TOKEN": ""
        }
    }' \
    "$VAULT_ADDR/v1/$VOYAGER_PATH/data/ai/providers" >/dev/null
log_ok "Created secret: voyager/ai/providers"

# Stripe payment processing
curl -sf -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" \
    -d '{
        "data": {
            "STRIPE_SECRET_KEY": "",
            "STRIPE_PUBLISHABLE_KEY": "",
            "STRIPE_WEBHOOK_SECRET": ""
        }
    }' \
    "$VAULT_ADDR/v1/$VOYAGER_PATH/data/stripe/credentials" >/dev/null
log_ok "Created secret: voyager/stripe/credentials"

# Email configuration
curl -sf -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" \
    -d '{
        "data": {
            "EMAIL_BACKEND": "smtp",
            "EMAIL_HOST": "",
            "EMAIL_PORT": "587",
            "EMAIL_USER": "",
            "EMAIL_PASSWORD": "",
            "EMAIL_USE_TLS": "true",
            "EMAIL_FROM": "noreply@voyager.local"
        }
    }' \
    "$VAULT_ADDR/v1/$VOYAGER_PATH/data/email/config" >/dev/null
log_ok "Created secret: voyager/email/config"

# Vortex workflow engine
curl -sf -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" \
    -d '{
        "data": {
            "VORTEX_URL": "http://vortex-core:11188",
            "VORTEX_API_KEY": ""
        }
    }' \
    "$VAULT_ADDR/v1/$VOYAGER_PATH/data/vortex/config" >/dev/null
log_ok "Created secret: voyager/vortex/config"

# =============================================================================
# STEP 3: Create ACL policies
# =============================================================================
log_info "Step 3: Creating ACL policies..."

# voyager-read policy
curl -sf -X PUT -H "$AUTH_HEADER" -H "Content-Type: application/json" \
    -d '{
        "policy": "path \"voyager/data/*\" { capabilities = [\"read\", \"list\"] }\npath \"voyager/data/django/config\" { capabilities = [\"read\"] }\npath \"voyager/data/database/credentials\" { capabilities = [\"read\"] }\npath \"voyager/data/platforms/api-keys\" { capabilities = [\"read\"] }\npath \"voyager/data/ai/providers\" { capabilities = [\"read\"] }\npath \"voyager/data/stripe/credentials\" { capabilities = [\"read\"] }\npath \"voyager/data/email/config\" { capabilities = [\"read\"] }\npath \"voyager/data/vortex/config\" { capabilities = [\"read\"] }"
    }' \
    "$VAULT_ADDR/v1/sys/policies/acl/voyager-read" >/dev/null
log_ok "Created policy: voyager-read"

# voyager-write policy
curl -sf -X PUT -H "$AUTH_HEADER" -H "Content-Type: application/json" \
    -d '{
        "policy": "path \"voyager/data/*\" { capabilities = [\"create\", \"read\", \"update\", \"delete\", \"list\"] }\npath \"voyager/metadata/*\" { capabilities = [\"list\", \"read\", \"delete\"] }\npath \"voyager/delete/*\" { capabilities = [\"update\"] }\npath \"voyager/destroy/*\" { capabilities = [\"update\"] }"
    }' \
    "$VAULT_ADDR/v1/sys/policies/acl/voyager-write" >/dev/null
log_ok "Created policy: voyager-write"

# voyager-api policy (service-specific: read-only for most, write for audit)
curl -sf -X PUT -H "$AUTH_HEADER" -H "Content-Type: application/json" \
    -d '{
        "policy": "path \"voyager/data/django/config\" { capabilities = [\"read\"] }\npath \"voyager/data/database/credentials\" { capabilities = [\"read\"] }\npath \"voyager/data/platforms/api-keys\" { capabilities = [\"read\"] }\npath \"voyager/data/ai/providers\" { capabilities = [\"read\"] }\npath \"voyager/data/stripe/credentials\" { capabilities = [\"read\"] }\npath \"voyager/data/email/config\" { capabilities = [\"read\"] }\npath \"voyager/data/vortex/config\" { capabilities = [\"read\"] }\npath \"voyager/data/audit/*\" { capabilities = [\"create\", \"read\"] }"
    }' \
    "$VAULT_ADDR/v1/sys/policies/acl/voyager-api" >/dev/null
log_ok "Created policy: voyager-api"

# =============================================================================
# STEP 4: Enable AppRole auth and create role for voyager-api
# =============================================================================
log_info "Step 4: Configuring AppRole authentication..."

# Check if AppRole is already enabled
EXISTING_AUTH=$(curl -sf -H "$AUTH_HEADER" "$VAULT_ADDR/v1/sys/auth" | jq -r '.data.approle // empty')

if [ -n "$EXISTING_AUTH" ]; then
    log_warn "AppRole auth already enabled, skipping"
else
    curl -sf -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" \
        -d '{"type": "approle", "description": "AppRole auth for Voyager services"}' \
        "$VAULT_ADDR/v1/sys/auth/approle" >/dev/null
    log_ok "Enabled AppRole authentication"
fi

# Create voyager-api AppRole
curl -sf -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" \
    -d '{
        "policies": ["voyager-api", "voyager-read"],
        "token_ttl": "1h",
        "token_max_ttl": "4h",
        "token_num_uses": 0,
        "secret_id_ttl": "24h",
        "secret_id_num_uses": 0,
        "bind_secret_id": true,
        "token_bound_cidrs": "",
        "secret_id_bound_cidrs": ""
    }' \
    "$VAULT_ADDR/v1/auth/approle/role/voyager-api" >/dev/null
log_ok "Created AppRole: voyager-api"

# Create voyager-worker AppRole
curl -sf -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" \
    -d '{
        "policies": ["voyager-read"],
        "token_ttl": "1h",
        "token_max_ttl": "4h",
        "token_num_uses": 0,
        "secret_id_ttl": "24h",
        "secret_id_num_uses": 0,
        "bind_secret_id": true
    }' \
    "$VAULT_ADDR/v1/auth/approle/role/voyager-worker" >/dev/null
log_ok "Created AppRole: voyager-worker"

# =============================================================================
# STEP 5: Read back credentials for configuration
# =============================================================================
log_info "Step 5: Retrieving AppRole credentials..."

# Get Role ID for voyager-api
VOYAGER_API_ROLE_ID=$(curl -sf -H "$AUTH_HEADER" "$VAULT_ADDR/v1/auth/approle/role/voyager-api/role-id" | jq -r '.data.role_id')
log_ok "voyager-api Role ID: $VOYAGER_API_ROLE_ID"

# Get Role ID for voyager-worker
VOYAGER_WORKER_ROLE_ID=$(curl -sf -H "$AUTH_HEADER" "$VAULT_ADDR/v1/auth/approle/role/voyager-worker/role-id" | jq -r '.data.role_id')
log_ok "voyager-worker Role ID: $VOYAGER_WORKER_ROLE_ID"

# =============================================================================
# STEP 6: Verify setup
# =============================================================================
log_info "Step 6: Verifying Vault setup..."

# List all secrets at voyager path
SECRETS_LIST=$(curl -sf -H "$AUTH_HEADER" "$VAULT_ADDR/v1/$VOYAGER_PATH/metadata/?list=true" 2>/dev/null | jq -r '.data.keys // []' || echo "[]")
log_ok "Secrets paths created: $SECRETS_LIST"

# Verify policies
POLICIES=$(curl -sf -H "$AUTH_HEADER" "$VAULT_ADDR/v1/sys/policies/acl?list=true" | jq -r '.data.keys[]' | grep voyager || true)
log_ok "Active Voyager policies: $(echo "$POLICIES" | tr '\n' ', ')"

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Voyager Vault Initialization Complete${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${BLUE}Vault Address:${NC}  $VAULT_ADDR"
echo -e "${BLUE}Secrets Path:${NC}   $VOYAGER_PATH"
echo ""
echo -e "${BLUE}AppRole Credentials:${NC}"
echo -e "  voyager-api Role ID:    ${YELLOW}$VOYAGER_API_ROLE_ID${NC}"
echo -e "  voyager-worker Role ID: ${YELLOW}$VOYAGER_WORKER_ROLE_ID${NC}"
echo ""
echo -e "${BLUE}To get a Secret ID for voyager-api:${NC}"
echo -e "  ${YELLOW}vault write -f auth/approle/role/voyager-api/secret-id${NC}"
echo ""
echo -e "${BLUE}To login with AppRole:${NC}"
echo -e "  ${YELLOW}vault write auth/approle/login role_id=<role-id> secret_id=<secret-id>${NC}"
echo ""
echo -e "${GREEN}All done!${NC}"
