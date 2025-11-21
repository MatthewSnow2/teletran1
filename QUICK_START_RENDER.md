# Chad-Core: Render Quick Start (15 Minutes)

**Goal**: Get Chad-Core running on Render with full capabilities for $7/month

**Prerequisites**: GitHub account, Render account, Upstash account, Cloudflare account

---

## ⚡ Super Quick Summary

1. **External Services** (10 min):
   - Create Upstash Redis (free) → Get `REDIS_URL`
   - Create Cloudflare R2 bucket (free) → Get R2 credentials
2. **Deploy to Render** (5 min):
   - Connect GitHub repo
   - Apply Blueprint (`render.yaml`)
   - Add environment variables
3. **Done!** → Test at `https://chad-core-api-xxx.onrender.com/healthz`

---

## 📝 Step-by-Step

### 1. Upstash Redis (2 minutes)

```bash
# 1. Go to: https://console.upstash.com
# 2. Click "Create Database"
#    Name: chad-core-redis
#    Type: Regional
#    Region: us-east-1 (or closest)
#    Plan: Free
# 3. Copy "Redis Connect URL" (starts with rediss://)
```

**Save**: `REDIS_URL=rediss://default:xxx@usw1-xxx.upstash.io:6379`

---

### 2. Cloudflare R2 (5 minutes)

```bash
# 1. Go to: https://dash.cloudflare.com
# 2. Enable R2 (left sidebar)
# 3. Create bucket:
#    Name: chad-core-artifacts
#    Location: Automatic
# 4. Create API Token:
#    - Go to "Manage R2 API Tokens"
#    - Permissions: Object Read & Write
#    - Create Token
# 5. Copy 3 values:
#    - Account ID
#    - Access Key ID
#    - Secret Access Key
```

**Save**:
```
R2_ACCOUNT_ID=xxx
R2_ACCESS_KEY_ID=xxx
R2_SECRET_ACCESS_KEY=xxx
```

---

### 3. Commit Files to GitHub (1 minute)

```bash
cd /workspace/chad-core

# Add new files
git add render.yaml requirements.txt chad_storage/
git add RENDER_DEPLOYMENT_GUIDE.md .env.production.template

# Commit
git commit -m "feat: add Render deployment configuration with R2 storage"

# Push
git push origin main
```

---

### 4. Deploy to Render (5 minutes)

#### 4.1 Connect Repository

1. Go to: https://dashboard.render.com
2. Click **"New +"** → **"Blueprint"**
3. **Connect GitHub** → Select `chad-core` repo
4. **Review**: Should show 1 Web Service + 1 Worker + 1 Database
5. Click **"Apply"**
6. Wait ~3 minutes for deployment

#### 4.2 Add Environment Variables

**For API Service** (`chad-core-api`):
1. Go to: Dashboard → Services → `chad-core-api` → Environment
2. **Add secrets** (click "Add Environment Variable"):

```bash
# Redis (from Upstash)
REDIS_URL=rediss://default:xxx@usw1-xxx.upstash.io:6379

# Cloudflare R2 (from step 2)
R2_ACCOUNT_ID=xxx
R2_ACCESS_KEY_ID=xxx
R2_SECRET_ACCESS_KEY=xxx

# LLM APIs (your existing keys)
OPENAI_API_KEY=sk-proj-xxx
ANTHROPIC_API_KEY=sk-ant-xxx

# Notion (your existing key)
NOTION_API_KEY=ntn_xxx
```

3. Click **"Save Changes"** → Service will auto-redeploy (~2 min)

**For Queue Worker** (`chad-core-queue-worker`):
1. Go to: Dashboard → Services → `chad-core-queue-worker` → Environment
2. **Add same secrets as API**
3. **IMPORTANT**: Also copy `JWT_SECRET_KEY` and `HMAC_SECRET_KEY` from API:
   - API → Environment → Click eye icon next to `JWT_SECRET_KEY` → Copy
   - Worker → Environment → Add `JWT_SECRET_KEY` → Paste
   - Repeat for `HMAC_SECRET_KEY`
4. Click **"Save Changes"**

---

### 5. Install pgvector Extension (2 minutes)

1. Go to: Dashboard → Databases → `chad-core-db` → Console
2. Run:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
3. Verify:
```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```
Should show: `vector | 0.5.0` (or higher)

---

### 6. Run Database Migrations (2 minutes)

**Option A: From Local Machine** (recommended)

```bash
# 1. Get DATABASE_URL from Render
# Dashboard → chad-core-db → Connection String (EXTERNAL)

export DATABASE_URL="postgresql+asyncpg://user:pass@dpg-xxx.render.com:5432/chad_core"

# 2. Run migrations
alembic upgrade head

# 3. Verify
psql $DATABASE_URL -c "\dt"
# Should show: runs, artifacts, embeddings, etc.
```

**Option B: From Render Shell**

```bash
# 1. Go to: Dashboard → chad-core-api → Shell
# 2. Run:
alembic upgrade head
```

---

### 7. Test Deployment (1 minute)

```bash
# 1. Get API URL from Render
# Dashboard → chad-core-api → Copy URL

# 2. Test health
curl https://chad-core-api-xxx.onrender.com/healthz
# Expected: {"status": "healthy"}

# 3. Test readiness
curl https://chad-core-api-xxx.onrender.com/readyz
# Expected: {"status": "ready", "database": "connected", "redis": "connected"}
```

---

## ✅ Success Checklist

- [ ] Upstash Redis created and URL saved
- [ ] Cloudflare R2 bucket created and credentials saved
- [ ] Code pushed to GitHub
- [ ] Render Blueprint applied successfully
- [ ] Environment variables added to API service
- [ ] Environment variables added to Worker service
- [ ] JWT/HMAC secrets copied from API to Worker
- [ ] pgvector extension installed
- [ ] Database migrations completed
- [ ] Health check returns 200 OK
- [ ] Readiness check shows database + redis connected

---

## 🎉 You're Done!

**Your API is live at**: `https://chad-core-api-xxx.onrender.com`

**Next Steps**:
1. Test with Notion: Run `test_real_notion.py` (update URL)
2. Test full agent: Run `test_e2e_simple.py` (update URL)
3. Connect n8n workflows to your API
4. Monitor logs: Dashboard → chad-core-api → Logs

---

## 💰 Cost Summary

- **Render Postgres**: $7/month (256MB)
- **Render API**: $0 (free tier)
- **Render Worker**: $0 (free tier)
- **Upstash Redis**: $0 (free tier)
- **Cloudflare R2**: $0 (10GB free)

**Total**: **$7/month**

---

## 🐛 Troubleshooting

**"Service is starting..." for >1 minute**
- Free tier has cold starts (~30-60s)
- Upgrade to Starter ($7/mo) for always-on

**"Database connection failed"**
```bash
# Check DATABASE_URL is correct
# API → Environment → DATABASE_URL should match database connection string
```

**"Redis connection timeout"**
```bash
# Test Redis from Render shell
redis-cli -u $REDIS_URL ping
# Expected: PONG
```

**"R2 upload failed"**
```bash
# Verify R2 credentials
# API → Environment → R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY
```

---

**For full deployment guide**: See [RENDER_DEPLOYMENT_GUIDE.md](./RENDER_DEPLOYMENT_GUIDE.md)

**Estimated Total Time**: **15-20 minutes**
