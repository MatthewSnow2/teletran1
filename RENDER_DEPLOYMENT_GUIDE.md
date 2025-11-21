# Chad-Core: Render Deployment Guide

**Date**: 2024-11-21
**Target**: Production deployment on Render.com
**Total Cost**: ~$7/month (Postgres only)
**Time to Deploy**: 45-60 minutes

---

## 🎯 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    RENDER WEB SERVICE                        │
│                 Chad-Core API (FastAPI)                      │
│                   Port 8000, Free Tier                       │
│              Spins down after 15min inactivity               │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Render       │  │ Upstash      │  │ Cloudflare   │
│ Postgres     │  │ Redis        │  │ R2           │
│ $7/month     │  │ FREE         │  │ FREE (10GB)  │
│ 256MB        │  │ 10k cmd/day  │  │ S3-compat    │
└──────────────┘  └──────────────┘  └──────────────┘
        ▲
        │
┌────────────────────────────────────────────────────────────┐
│              RENDER BACKGROUND WORKER                       │
│            Chad-Core Queue Worker (Python)                  │
│                   Free Tier (Always-On)                     │
└────────────────────────────────────────────────────────────┘
```

**Total Monthly Cost**: $7 (just Postgres)

---

## 📋 Prerequisites

Before starting, ensure you have:

- [x] Render.com account (sign up at render.com)
- [x] GitHub account (for git deployment)
- [x] Upstash account (sign up at upstash.com)
- [x] Cloudflare account (sign up at cloudflare.com)
- [x] Chad-core repository pushed to GitHub

---

## 🚀 Part 1: External Services Setup

### Step 1.1: Upstash Redis (FREE)

**Why**: Working memory, rate limiting, idempotency cache

1. **Sign up**: Go to [console.upstash.com](https://console.upstash.com)
2. **Create database**:
   - Click "Create Database"
   - Name: `chad-core-redis`
   - Type: **Regional**
   - Region: Choose closest to you (e.g., `us-east-1`)
   - Plan: **Free** (10,000 commands/day)
3. **Get connection string**:
   - Go to database details
   - Copy **Redis Connect URL** (starts with `rediss://`)
   - Example: `rediss://default:xxxxx@usw1-chad-12345.upstash.io:6379`
4. **Save for later**: Store in password manager

**Expected result**: Redis URL in format `rediss://default:PASSWORD@HOST:6379`

---

### Step 1.2: Cloudflare R2 Storage (FREE 10GB)

**Why**: Artifact storage (PDFs, images, generated files)

1. **Sign up**: Go to [dash.cloudflare.com](https://dash.cloudflare.com)
2. **Enable R2**:
   - Left sidebar → R2
   - Click "Enable R2"
   - (No credit card required for 10GB free tier)
3. **Create bucket**:
   - Click "Create bucket"
   - Name: `chad-core-artifacts`
   - Location: **Automatic**
   - Click "Create bucket"
4. **Create API Token**:
   - Go to "Manage R2 API Tokens"
   - Click "Create API Token"
   - Permissions: **Object Read & Write**
   - Click "Create API Token"
5. **Save credentials**:
   ```bash
   R2_ACCOUNT_ID=<your_account_id>
   R2_ACCESS_KEY_ID=<access_key_id>
   R2_SECRET_ACCESS_KEY=<secret_access_key>
   R2_BUCKET_NAME=chad-core-artifacts
   R2_ENDPOINT=https://<account_id>.r2.cloudflarestorage.com
   ```

**Expected result**: 5 R2 credentials saved

---

## 🗄️ Part 2: Render Database Setup

### Step 2.1: Create Render Postgres Database

1. **Login to Render**: [dashboard.render.com](https://dashboard.render.com)
2. **Create PostgreSQL**:
   - Click "New +" → "PostgreSQL"
   - **Name**: `chad-core-db`
   - **Database**: `chad_core` (default)
   - **User**: `chad_core_user` (auto-generated)
   - **Region**: Same as your API (e.g., Oregon, Ohio)
   - **Plan**: **Starter** ($7/month, 256MB)
   - Click "Create Database"
3. **Wait for provisioning** (~2 minutes)
4. **Install pgvector extension**:
   - Go to database dashboard
   - Click "Console" tab
   - Run:
     ```sql
     CREATE EXTENSION IF NOT EXISTS vector;
     ```
   - Verify:
     ```sql
     SELECT * FROM pg_extension WHERE extname = 'vector';
     ```
   - Should show version 0.5.0+

5. **Get connection strings**:
   - **Internal URL** (for API/Worker): `postgresql://user:pass@dpg-xxxxx:5432/chad_core`
   - **External URL** (for migrations): `postgresql://user:pass@dpg-xxxxx.render.com:5432/chad_core`

   **For Chad-Core, use asyncpg driver**:
   ```bash
   # Internal (API uses this)
   DATABASE_URL=postgresql+asyncpg://user:pass@dpg-xxxxx:5432/chad_core

   # External (for Alembic migrations from local)
   DATABASE_URL_EXTERNAL=postgresql+asyncpg://user:pass@dpg-xxxxx.render.com:5432/chad_core
   ```

6. **Save URLs**: Store both internal and external URLs

**Expected result**:
- ✅ Postgres database running
- ✅ pgvector extension installed
- ✅ 2 connection URLs saved

---

## 📦 Part 3: Prepare Code for Deployment

### Step 3.1: Create Render Configuration File

Create `render.yaml` in project root:

```yaml
# render.yaml - Chad-Core Infrastructure as Code
# Deploys: API + Queue Worker + Postgres

services:
  # ============================================================================
  # API SERVICE (FastAPI)
  # ============================================================================
  - type: web
    name: chad-core-api
    runtime: python
    plan: free  # Free tier (spins down after 15min)
    region: oregon  # Change to your preferred region
    branch: main
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn apps.core_api.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /healthz

    envVars:
      # Database (from Render Postgres)
      - key: DATABASE_URL
        fromDatabase:
          name: chad-core-db
          property: connectionString

      # Redis (Upstash - manual entry)
      - key: REDIS_URL
        sync: false  # Set in Render dashboard

      # LLM APIs (manual entry)
      - key: OPENAI_API_KEY
        sync: false
      - key: ANTHROPIC_API_KEY
        sync: false

      # Notion (manual entry)
      - key: NOTION_API_KEY
        sync: false

      # Cloudflare R2 (manual entry)
      - key: R2_ACCOUNT_ID
        sync: false
      - key: R2_ACCESS_KEY_ID
        sync: false
      - key: R2_SECRET_ACCESS_KEY
        sync: false
      - key: R2_BUCKET_NAME
        value: chad-core-artifacts

      # Auth secrets (auto-generated)
      - key: JWT_SECRET_KEY
        generateValue: true
      - key: HMAC_SECRET_KEY
        generateValue: true

      # Configuration
      - key: ENVIRONMENT
        value: production
      - key: LOG_LEVEL
        value: INFO
      - key: EMBED_INDEX_TYPE
        value: HNSW
      - key: API_CORS_ORIGINS
        value: https://your-frontend.netlify.app
      - key: ARTIFACT_STORAGE_TYPE
        value: r2

  # ============================================================================
  # QUEUE WORKER (Background Jobs)
  # ============================================================================
  - type: worker
    name: chad-core-queue-worker
    runtime: python
    plan: free  # Free tier (always-on)
    region: oregon
    branch: main
    buildCommand: pip install -r requirements.txt
    startCommand: python -m apps.queue_worker.main

    envVars:
      # Database (from Render Postgres)
      - key: DATABASE_URL
        fromDatabase:
          name: chad-core-db
          property: connectionString

      # Redis (Upstash - manual entry)
      - key: REDIS_URL
        sync: false

      # LLM APIs (manual entry)
      - key: OPENAI_API_KEY
        sync: false
      - key: ANTHROPIC_API_KEY
        sync: false

      # Notion (manual entry)
      - key: NOTION_API_KEY
        sync: false

      # Cloudflare R2 (manual entry)
      - key: R2_ACCOUNT_ID
        sync: false
      - key: R2_ACCESS_KEY_ID
        sync: false
      - key: R2_SECRET_ACCESS_KEY
        sync: false
      - key: R2_BUCKET_NAME
        value: chad-core-artifacts

      # Auth secrets (shared with API)
      - key: JWT_SECRET_KEY
        sync: false  # Copy from API
      - key: HMAC_SECRET_KEY
        sync: false  # Copy from API

      # Configuration
      - key: ENVIRONMENT
        value: production
      - key: LOG_LEVEL
        value: INFO

# ============================================================================
# DATABASE (PostgreSQL + pgvector)
# ============================================================================
databases:
  - name: chad-core-db
    plan: starter  # $7/month, 256MB
    region: oregon
    databaseName: chad_core
    user: chad_core_user
    postgresMajorVersion: 15

    # Extensions to install
    ipAllowList: []  # Allow all IPs (or restrict to your IP)
```

**Commit this file**:
```bash
git add render.yaml
git commit -m "feat: add Render deployment configuration"
git push origin main
```

---

### Step 3.2: Add R2 Storage Client

Chad-Core currently uses Supabase Storage. We need to add R2 support.

Create `chad_storage/__init__.py`:

```python
"""Artifact storage abstraction layer.

Supports:
- Cloudflare R2 (S3-compatible)
- Supabase Storage (legacy)
- Local disk (development)
"""

import os
from typing import Protocol
import boto3
from botocore.config import Config


class StorageClient(Protocol):
    """Storage client interface."""

    async def upload_file(self, key: str, content: bytes, content_type: str) -> str:
        """Upload file and return public URL."""
        ...

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Get presigned URL for download."""
        ...

    async def delete_file(self, key: str) -> None:
        """Delete file."""
        ...


class CloudflareR2Client:
    """Cloudflare R2 storage client (S3-compatible)."""

    def __init__(
        self,
        account_id: str,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
    ):
        """Initialize R2 client.

        Args:
            account_id: Cloudflare account ID
            access_key_id: R2 access key ID
            secret_access_key: R2 secret access key
            bucket_name: R2 bucket name
        """
        self.bucket_name = bucket_name

        # R2 endpoint format
        endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"

        # Create S3 client (R2 is S3-compatible)
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=Config(signature_version="s3v4"),
        )

    async def upload_file(self, key: str, content: bytes, content_type: str) -> str:
        """Upload file to R2.

        Args:
            key: Object key (path)
            content: File content
            content_type: MIME type

        Returns:
            Public URL (if bucket is public) or key
        """
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

        # Return key (use presigned URL for downloads)
        return key

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate presigned download URL.

        Args:
            key: Object key
            expires_in: URL expiration in seconds

        Returns:
            Presigned URL
        """
        url = self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )
        return url

    async def delete_file(self, key: str) -> None:
        """Delete file from R2."""
        self.s3.delete_object(Bucket=self.bucket_name, Key=key)


def get_storage_client() -> StorageClient:
    """Get storage client based on environment configuration.

    Returns:
        StorageClient instance
    """
    storage_type = os.getenv("ARTIFACT_STORAGE_TYPE", "r2")

    if storage_type == "r2":
        return CloudflareR2Client(
            account_id=os.getenv("R2_ACCOUNT_ID"),
            access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
            bucket_name=os.getenv("R2_BUCKET_NAME", "chad-core-artifacts"),
        )
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")
```

**Add boto3 dependency**:

Add to `requirements.txt`:
```
boto3>=1.28.0
```

**Commit**:
```bash
mkdir -p chad_storage
# (create __init__.py with content above)
git add chad_storage/ requirements.txt
git commit -m "feat: add Cloudflare R2 storage client"
git push origin main
```

---

## 🚢 Part 4: Deploy to Render

### Step 4.1: Connect GitHub Repository to Render

1. **Go to Render Dashboard**: [dashboard.render.com](https://dashboard.render.com)
2. **Click "New +"** → "Blueprint"
3. **Connect GitHub**:
   - Click "Connect GitHub"
   - Authorize Render
   - Select `chad-core` repository
4. **Review Blueprint**:
   - Render will parse `render.yaml`
   - Should show:
     - ✅ 1x Web Service (chad-core-api)
     - ✅ 1x Worker (chad-core-queue-worker)
     - ✅ 1x PostgreSQL (chad-core-db)
5. **Apply Blueprint**:
   - Click "Apply"
   - Wait for deployment (~5 minutes)

**What happens**:
- Creates Postgres database
- Builds API Docker image
- Builds Worker Docker image
- Starts both services

---

### Step 4.2: Set Environment Variables

After deployment, set the manual environment variables:

1. **Go to API Service**:
   - Dashboard → Services → `chad-core-api`
   - Click "Environment" tab

2. **Add variables**:
   ```bash
   # Redis (from Upstash)
   REDIS_URL=rediss://default:xxxxx@usw1-chad.upstash.io:6379

   # LLM APIs
   OPENAI_API_KEY=sk-proj-xxxxx
   ANTHROPIC_API_KEY=sk-ant-xxxxx

   # Notion
   NOTION_API_KEY=ntn_xxxxx

   # Cloudflare R2
   R2_ACCOUNT_ID=xxxxx
   R2_ACCESS_KEY_ID=xxxxx
   R2_SECRET_ACCESS_KEY=xxxxx
   ```

3. **Save Changes** → Service will auto-redeploy

4. **Repeat for Queue Worker**:
   - Dashboard → Services → `chad-core-queue-worker`
   - Add same variables
   - **IMPORTANT**: Copy `JWT_SECRET_KEY` and `HMAC_SECRET_KEY` from API
     - Go to API → Environment → Click eye icon to reveal
     - Copy both secrets to Worker

---

### Step 4.3: Run Database Migrations

**Option A: From Local Machine** (Recommended for first time)

```bash
# 1. Get external DATABASE_URL from Render dashboard
export DATABASE_URL="postgresql+asyncpg://user:pass@dpg-xxxxx.render.com:5432/chad_core"

# 2. Run migrations
alembic upgrade head

# 3. Verify tables created
psql $DATABASE_URL -c "\dt"
# Should show: runs, artifacts, embeddings, etc.
```

**Option B: From Render Shell**

```bash
# 1. Go to API service → Shell tab
# 2. Run:
alembic upgrade head
```

**Expected result**:
```
INFO  [alembic.runtime.migration] Running upgrade -> 001_initial
INFO  [alembic.runtime.migration] Running upgrade 001_initial -> 002_add_pgvector
✅ Database migrated successfully
```

---

## ✅ Part 5: Verify Deployment

### Step 5.1: Check Service Health

1. **Get API URL**:
   - Dashboard → `chad-core-api` → Copy URL
   - Example: `https://chad-core-api-abc123.onrender.com`

2. **Test health endpoint**:
   ```bash
   curl https://chad-core-api-abc123.onrender.com/healthz
   # Expected: {"status": "healthy"}
   ```

3. **Test readiness**:
   ```bash
   curl https://chad-core-api-abc123.onrender.com/readyz
   # Expected: {"status": "ready", "database": "connected", "redis": "connected"}
   ```

4. **Check metrics**:
   ```bash
   curl https://chad-core-api-abc123.onrender.com/metrics
   # Should return Prometheus metrics
   ```

---

### Step 5.2: Test /act Endpoint

Generate test JWT token locally:

```python
# test_token.py
from apps.core_api.auth import generate_jwt_token

token = generate_jwt_token(
    actor="test_user",
    scopes=["notion.*", "github.read"]
)
print(f"Token: {token.access_token}")
```

Run:
```bash
python test_token.py
# Copy token
```

Test /act:
```bash
curl -X POST https://chad-core-api-abc123.onrender.com/act \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "X-HMAC-Signature: test_sig" \
  -d '{
    "actor": "test_user",
    "goal": "Search my Notion workspace for pages about testing",
    "context": {},
    "max_steps": 5,
    "dry_run": false
  }'
```

**Expected response**:
```json
{
  "run_id": "550e8400-...",
  "trace_id": "abcd1234...",
  "status": "pending",
  "poll_url": "/runs/550e8400-..."
}
```

---

### Step 5.3: Monitor Logs

**Real-time logs**:
1. Dashboard → `chad-core-api` → Logs tab
2. Watch for:
   - ✅ `"event": "http_request_complete"`
   - ✅ `"status_code": 200`
   - ❌ Any errors

**Queue Worker logs**:
1. Dashboard → `chad-core-queue-worker` → Logs tab
2. Should show:
   - ✅ `"event": "queue_worker_started"`
   - ✅ `"event": "consuming_from_stream"`

---

## 🔒 Part 6: Security Hardening

### Step 6.1: Restrict Database Access

1. **Go to Database**:
   - Dashboard → `chad-core-db` → Settings
2. **IP Allowlist**:
   - By default: Allow all (0.0.0.0/0)
   - **Production**: Restrict to Render IPs only
   - Add your local IP for migrations

### Step 6.2: Rotate Secrets

```bash
# Generate new secrets
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update in Render:
# 1. API → Environment → JWT_SECRET_KEY → Update
# 2. Worker → Environment → JWT_SECRET_KEY → Update (same value)
```

### Step 6.3: Enable HTTPS Only

Render provides HTTPS by default. Verify:
```bash
curl -I http://chad-core-api-abc123.onrender.com
# Should redirect to HTTPS
```

---

## 📊 Part 7: Monitoring & Observability

### Step 7.1: Render Metrics (Built-in)

1. **Go to API Service** → Metrics tab
2. **View**:
   - Request rate
   - Response time
   - Memory usage
   - CPU usage

### Step 7.2: Set Up Alerts

1. **Go to API Service** → Notifications
2. **Add alert**:
   - Trigger: Service becomes unavailable
   - Notify: Email
   - Threshold: 5 minutes downtime

### Step 7.3: External Monitoring (Optional)

**BetterStack** (free tier):
1. Sign up at betterstack.com
2. Add HTTP monitor:
   - URL: `https://chad-core-api-abc123.onrender.com/healthz`
   - Interval: 1 minute
   - Expected: `200 OK`

---

## 🐛 Troubleshooting

### Issue: "Service is starting..."

**Cause**: Cold start (free tier spins down after 15min)
**Solution**: Wait 30-60 seconds for spin-up
**Prevention**: Upgrade to paid plan ($7/mo) for always-on

---

### Issue: "Database connection failed"

**Check**:
1. Postgres is running: Dashboard → `chad-core-db` → Status
2. DATABASE_URL is correct: API → Environment
3. Migrations ran: API → Shell → `alembic current`

**Fix**:
```bash
# Re-run migrations
alembic upgrade head
```

---

### Issue: "Redis connection timeout"

**Check**:
1. REDIS_URL is correct: API → Environment
2. Upstash database is running: console.upstash.com

**Fix**:
```bash
# Test Redis from Render shell
redis-cli -u $REDIS_URL ping
# Expected: PONG
```

---

### Issue: "R2 upload failed"

**Check**:
1. R2 credentials: API → Environment
2. Bucket exists: Cloudflare → R2
3. API token permissions: R2 → Manage API Tokens

**Fix**:
```bash
# Test R2 from shell
python -c "
from chad_storage import get_storage_client
client = get_storage_client()
url = await client.upload_file('test.txt', b'hello', 'text/plain')
print(f'Uploaded: {url}')
"
```

---

## 📝 Post-Deployment Checklist

- [ ] ✅ API health check returns 200
- [ ] ✅ Queue worker logs show "consuming_from_stream"
- [ ] ✅ Database has tables (runs, artifacts, embeddings)
- [ ] ✅ Can authenticate with JWT
- [ ] ✅ Can execute /act endpoint
- [ ] ✅ Redis connection works
- [ ] ✅ R2 uploads work
- [ ] ✅ Notion integration works
- [ ] ✅ Monitoring alerts configured
- [ ] ✅ Secrets rotated from defaults

---

## 💰 Cost Summary

| Service | Plan | Cost | Notes |
|---------|------|------|-------|
| Render Postgres | Starter | $7/mo | 256MB, automated backups |
| Render API | Free | $0 | Spins down after 15min |
| Render Worker | Free | $0 | Always-on |
| Upstash Redis | Free | $0 | 10k commands/day |
| Cloudflare R2 | Free | $0 | 10GB storage |
| **TOTAL** | | **$7/month** | |

**Upgrade path** (if needed):
- Render API to Starter ($7/mo) → Always-on, no cold starts
- Render Postgres to Standard ($20/mo) → 1GB, better performance
- Upstash to paid ($10/mo) → Unlimited commands
- **Total with upgrades**: ~$37/month

---

## 🎉 Success!

Your Chad-Core is now running on Render with:
- ✅ Production Postgres database (pgvector enabled)
- ✅ Redis working memory (Upstash)
- ✅ Artifact storage (Cloudflare R2)
- ✅ API service (auto-scaling)
- ✅ Queue worker (background jobs)
- ✅ Full observability (logs, metrics, traces)

**Next Steps**:
1. Run end-to-end test: `python test_e2e_simple.py` (update URL)
2. Connect n8n workflows to production API
3. Set up frontend (Netlify) to call API
4. Monitor costs and performance

**Support**: If you encounter issues, check:
- Render status: status.render.com
- Upstash status: status.upstash.com
- Cloudflare status: www.cloudflarestatus.com

---

**Deployed by**: Claude Code
**Date**: 2024-11-21
**Version**: 1.0.0
