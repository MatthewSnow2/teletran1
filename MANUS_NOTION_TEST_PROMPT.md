# Manus Test Prompt: Chad-Core Notion Integration E2E Testing

**Agent**: Manus (Browser Agent)
**Task**: Comprehensive end-to-end testing of chad-core's Notion workspace integration
**Duration**: 30-45 minutes
**Tools Required**: Browser automation (Playwright), API testing, Notion workspace access

---

## 🎯 Testing Objective

Validate that chad-core can autonomously organize a Notion workspace by:
1. Discovering and searching pages
2. Reading page content with accuracy
3. Categorizing pages using dual-LLM intelligence (Claude for analysis, ChatGPT for summaries)
4. Creating structured index pages
5. Maintaining a master knowledge base index

---

## 📋 Pre-Test Setup Requirements

### 1. Verify Environment Configuration
```bash
# Navigate to project
cd /workspace/chad-core

# Check .env file has required keys
grep -E "NOTION_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|DATABASE_URL|REDIS_URL" .env

# Verify all keys are populated (not placeholder values)
```

**Expected**: All 5 environment variables should have real values, not "placeholder" or "CHANGE_ME"

### 2. Start Required Services
```bash
# Start Docker services (Redis, Postgres)
make docker-up

# Wait 10 seconds for services to initialize
sleep 10

# Run database migrations
make migrate

# Verify Redis is running
redis-cli ping
# Expected output: PONG

# Verify Postgres is running
psql $DATABASE_URL -c "SELECT version();"
# Expected: PostgreSQL version output
```

### 3. Create Test Notion Workspace Content

**Manual Step** (or use browser automation):
- Open Notion workspace in browser
- Create a test section with 8-12 pages across different topics:
  - **Programming Pages**: "Python Best Practices", "API Design Guide", "Git Workflow"
  - **Project Pages**: "Chad-Core Development", "Portfolio Website", "Mobile App Idea"
  - **Personal Pages**: "Meeting Notes 2024-11-18", "Weekly Goals", "Book Recommendations"
  - **Random Pages**: "Grocery List", "Travel Plans", "Fitness Routine"

**Browser Automation Task**: Navigate to Notion, verify test pages exist, screenshot the workspace structure.

---

## 🧪 Test Phase 1: Notion Search Integration

### Test 1.1: Basic Search Functionality
```bash
# Start the chad-core API in background
make run &
API_PID=$!
sleep 5

# Test search endpoint via curl
curl -X POST http://localhost:8000/tools/notion.search/execute \
  -H "Content-Type: application/json" \
  -d '{
    "actor": "test_user",
    "input_data": {
      "query": "",
      "max_results": 20
    }
  }' | jq
```

**Expected Results**:
- ✅ HTTP 200 status
- ✅ JSON response with "results" array
- ✅ At least 8 pages returned (matching test content)
- ✅ Each result has: `id`, `title`, `type`, `url`, `last_edited_time`

**Browser Validation**:
- Open Notion in browser
- Count total accessible pages
- Verify API returned count matches browser count (±2 for system pages)

### Test 1.2: Filtered Search
```bash
# Search for "Python" keyword
curl -X POST http://localhost:8000/tools/notion.search/execute \
  -H "Content-Type: application/json" \
  -d '{
    "actor": "test_user",
    "input_data": {
      "query": "Python",
      "max_results": 10
    }
  }' | jq '.results[] | {title, url}'
```

**Expected**:
- ✅ Returns only Python-related pages
- ✅ "Python Best Practices" appears in results
- ✅ Non-Python pages excluded

**Browser Validation**:
- Search "Python" in Notion's search bar
- Compare browser results with API results
- Screenshot both for comparison

---

## 🧪 Test Phase 2: Page Reading & Content Extraction

### Test 2.1: Read Single Page
```bash
# First, get a page_id from search results
PAGE_ID=$(curl -s -X POST http://localhost:8000/tools/notion.search/execute \
  -H "Content-Type: application/json" \
  -d '{"actor":"test_user","input_data":{"query":"Python","max_results":1}}' \
  | jq -r '.results[0].id')

echo "Testing page_id: $PAGE_ID"

# Read the page content
curl -X POST http://localhost:8000/tools/notion.pages.read/execute \
  -H "Content-Type: application/json" \
  -d "{
    \"actor\": \"test_user\",
    \"input_data\": {
      \"page_id\": \"$PAGE_ID\"
    }
  }" | jq
```

**Expected**:
- ✅ HTTP 200 status
- ✅ Response contains: `title`, `markdown`, `url`, `properties`, `last_edited_time`
- ✅ Markdown content is non-empty
- ✅ Markdown accurately represents page structure

**Browser Validation**:
1. Open the page URL (from response) in browser
2. Compare rendered content with API markdown
3. Verify headings, lists, formatting preserved
4. Screenshot for documentation

### Test 2.2: Read Multiple Pages (Batch Test)
```bash
# Get 3 page IDs
PAGE_IDS=$(curl -s -X POST http://localhost:8000/tools/notion.search/execute \
  -H "Content-Type: application/json" \
  -d '{"actor":"test_user","input_data":{"query":"","max_results":3}}' \
  | jq -r '.results[].id')

# Read each page and measure response time
for page_id in $PAGE_IDS; do
  echo "Reading page: $page_id"
  time curl -s -X POST http://localhost:8000/tools/notion.pages.read/execute \
    -H "Content-Type: application/json" \
    -d "{\"actor\":\"test_user\",\"input_data\":{\"page_id\":\"$page_id\"}}" \
    | jq '.title'
done
```

**Expected**:
- ✅ All 3 pages read successfully
- ✅ Average response time < 2 seconds per page
- ✅ No rate limit errors (Notion allows 3 req/s)

---

## 🧪 Test Phase 3: Autonomous Agent Workflow (Core Test)

### Test 3.1: Execute Knowledge Organization Workflow

**This is the primary test - it validates the entire system.**

```bash
# Generate JWT token for authentication
JWT_TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "actor": "test_user",
    "scopes": ["notion.*", "admin"]
  }' | jq -r '.access_token')

# Compute HMAC signature
REQUEST_BODY='{
  "actor": "test_user",
  "goal": "Organize all pages in my Notion workspace by topic and create a master index",
  "context": {},
  "max_steps": 15,
  "timeout_seconds": 180,
  "dry_run": false
}'

HMAC_SIG=$(echo -n "$REQUEST_BODY" | openssl dgst -sha256 -hmac "$(grep HMAC_SECRET_KEY .env | cut -d= -f2)" | awk '{print $2}')

# Execute /act endpoint (triggers LangGraph agent)
curl -X POST http://localhost:8000/act \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "X-HMAC-Signature: $HMAC_SIG" \
  -d "$REQUEST_BODY" > /tmp/act_response.json

cat /tmp/act_response.json | jq

# Extract run_id for polling
RUN_ID=$(jq -r '.run_id' /tmp/act_response.json)
echo "Execution run_id: $RUN_ID"
```

**Expected Initial Response** (202 Accepted):
```json
{
  "run_id": "550e8400-...",
  "status": "pending",
  "poll_url": "/runs/550e8400-...",
  "autonomy_level": "L2_ExecuteNotify"
}
```

### Test 3.2: Poll Execution Status
```bash
# Poll every 10 seconds for up to 3 minutes
for i in {1..18}; do
  echo "Poll attempt $i/18..."

  RESPONSE=$(curl -s http://localhost:8000/runs/$RUN_ID)
  STATUS=$(echo "$RESPONSE" | jq -r '.status')

  echo "Status: $STATUS"
  echo "$RESPONSE" | jq '.executed_steps[-1] | {step, tool, status}' 2>/dev/null

  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    echo "Execution finished: $STATUS"
    echo "$RESPONSE" | jq '.' > /tmp/final_result.json
    break
  fi

  sleep 10
done

# Display final results
cat /tmp/final_result.json | jq
```

**Expected Execution Steps** (from LangGraph):
1. **Plan Node** (Claude generates plan)
2. **Execute**: `notion.search` (discover all pages)
3. **Reflect** (Claude evaluates results)
4. **Execute**: `notion.pages.read` x N (read each page)
5. **Reflect** (check if all content gathered)
6. **Execute**: LLM categorization (Claude analyzes topics)
7. **Execute**: `notion.pages.create` (create category index pages)
8. **Execute**: `notion.pages.create` (create master index)
9. **Reflect** (validate goal achieved)
10. **Finalize** (generate notification)

**Expected Final Status**:
```json
{
  "run_id": "550e8400-...",
  "status": "completed",
  "autonomy_level": "L2_ExecuteNotify",
  "final_result": {
    "status": "completed",
    "artifacts": [
      {
        "type": "notion_page",
        "title": "📁 Programming",
        "url": "https://notion.so/..."
      },
      {
        "type": "notion_page",
        "title": "📚 Knowledge Base Index",
        "url": "https://notion.so/..."
      }
    ],
    "steps_executed": 8,
    "llm_calls": 3,
    "duration_seconds": 45
  }
}
```

---

## 🧪 Test Phase 4: Browser Validation of Results

### Test 4.1: Verify Created Pages in Notion

**Browser Automation Task**:

```javascript
// Playwright script to validate Notion results
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  // 1. Login to Notion (use session from environment)
  await page.goto('https://notion.so');
  await page.waitForTimeout(2000);

  // 2. Search for master index page
  await page.keyboard.press('Control+K'); // Cmd+K on Mac
  await page.fill('[placeholder="Search..."]', 'Knowledge Base Index');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: '/tmp/notion_search.png' });

  // 3. Open master index page
  await page.click('text=📚 Knowledge Base Index');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/master_index.png' });

  // 4. Extract created index pages from content
  const indexLinks = await page.$$eval('a[href*="notion.so"]', links =>
    links.map(l => ({ text: l.textContent, href: l.href }))
  );

  console.log('Index pages found:', indexLinks);

  // 5. Validate each category index page
  for (const link of indexLinks.filter(l => l.text.includes('📁'))) {
    await page.goto(link.href);
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `/tmp/category_${link.text.replace(/[^a-z0-9]/gi, '_')}.png` });

    // Check for page links
    const pageLinks = await page.$$eval('a[href*="notion.so"]', links => links.length);
    console.log(`${link.text} contains ${pageLinks} page links`);
  }

  await browser.close();
})();
```

**Expected Browser Validation**:
- ✅ Master index page exists with title "📚 Knowledge Base Index"
- ✅ 3-5 category index pages created (e.g., "📁 Programming", "📋 Projects", "📝 Personal")
- ✅ Each category page contains links to relevant original pages
- ✅ Category summaries are present (generated by ChatGPT-5)
- ✅ Last updated timestamp shows current date
- ✅ Auto-generated attribution footer present

### Test 4.2: Validate LLM Routing

**Check which LLM was used for each task**:

```bash
# Extract LLM usage from execution logs
grep -E "LLM|model_name" /tmp/final_result.json

# Expected:
# - Planning: claude-3-5-sonnet (technical reasoning)
# - Categorization: claude-3-5-sonnet (analysis)
# - Summaries: gpt-4o (user-friendly text)
# - Notification: gpt-4o (conversational)
```

**Browser Check**:
- Open a category index page
- Read the summary text
- Verify it's conversational and user-friendly (ChatGPT style)
- Check reasoning quality in categorization (Claude style)

---

## 🧪 Test Phase 5: Error Handling & Edge Cases

### Test 5.1: Invalid Page ID
```bash
curl -X POST http://localhost:8000/tools/notion.pages.read/execute \
  -H "Content-Type: application/json" \
  -d '{
    "actor": "test_user",
    "input_data": {
      "page_id": "invalid-page-id-12345"
    }
  }'
```

**Expected**:
- ✅ HTTP 400 or 404 error
- ✅ Clear error message: "Page not found" or "Invalid page_id"
- ✅ No server crash

### Test 5.2: Rate Limiting
```bash
# Send 10 rapid requests
for i in {1..10}; do
  curl -X POST http://localhost:8000/tools/notion.search/execute \
    -H "Content-Type: application/json" \
    -d '{"actor":"test_user","input_data":{"query":"test","max_results":5}}' &
done
wait
```

**Expected**:
- ✅ Some requests may get HTTP 429 (Too Many Requests)
- ✅ Rate limit respects Notion's 3 req/s limit
- ✅ No Notion API errors

### Test 5.3: Empty Workspace Handling
```bash
# Create a goal for empty workspace (if no pages exist)
curl -X POST http://localhost:8000/act \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "X-HMAC-Signature: $HMAC_SIG" \
  -d '{
    "actor": "test_user",
    "goal": "Organize my Notion workspace",
    "context": {},
    "max_steps": 5
  }'
```

**Expected**:
- ✅ Agent completes without errors
- ✅ Final result explains no pages found
- ✅ No index pages created (nothing to organize)

---

## 🧪 Test Phase 6: Observability & Metrics

### Test 6.1: Prometheus Metrics
```bash
# Check metrics endpoint
curl http://localhost:8000/metrics | grep -E "tool_executions|autonomy_level|agent_loop"
```

**Expected Metrics**:
```
tool_executions_total{tool="notion.search",status="success"} 5
tool_executions_total{tool="notion.pages.read",status="success"} 12
tool_executions_total{tool="notion.pages.create",status="success"} 4
autonomy_level_total{level="L2_ExecuteNotify"} 1
agent_loop_duration_seconds_sum 45.3
```

### Test 6.2: Structured Logging
```bash
# Check logs for structured JSON output
docker logs chad-core-api 2>&1 | tail -50 | jq 'select(.event == "agent_execution_complete")'
```

**Expected**:
- ✅ JSON-formatted logs
- ✅ Contains: `trace_id`, `actor`, `status`, `duration_ms`
- ✅ No error-level logs for successful execution

### Test 6.3: Health Checks
```bash
# Health check
curl http://localhost:8000/healthz

# Readiness check
curl http://localhost:8000/readyz
```

**Expected**:
```json
{"status": "healthy", "timestamp": "2024-11-20T..."}
```

---

## 📊 Test Results Summary

### Checklist

**Notion Integration**:
- [ ] Search returns accurate results
- [ ] Page reading preserves markdown structure
- [ ] Rate limiting prevents API abuse
- [ ] Error handling for invalid requests

**Autonomous Agent**:
- [ ] /act endpoint accepts requests
- [ ] LangGraph executes plan → execute → reflect loop
- [ ] Claude used for planning and analysis
- [ ] ChatGPT used for summaries and notifications
- [ ] Index pages created successfully
- [ ] Master index links to all category pages

**Browser Validation**:
- [ ] Created pages visible in Notion workspace
- [ ] Category organization is logical
- [ ] Summaries are accurate and readable
- [ ] Links function correctly
- [ ] Timestamps are current

**System Health**:
- [ ] No crashes or exceptions
- [ ] Metrics accurately track operations
- [ ] Logs provide clear audit trail
- [ ] Health checks pass

---

## 📸 Evidence Collection

**Screenshots to Capture**:
1. Notion workspace before test
2. Notion search results (browser)
3. Master index page (after agent execution)
4. Each category index page
5. Example original page linked from index
6. API response for /act endpoint
7. Final execution status from /runs/{id}
8. Prometheus metrics dashboard
9. Structured logs (last 50 lines)

**Files to Save**:
- `/tmp/act_response.json` - Initial 202 response
- `/tmp/final_result.json` - Completed execution details
- `/tmp/notion_search.png` - Notion UI screenshot
- `/tmp/master_index.png` - Master index screenshot
- All category screenshots

---

## 🎯 Success Criteria

**This test passes if**:
1. ✅ Agent successfully organizes 8+ pages into 3-5 categories
2. ✅ Master index page created with all category links
3. ✅ Category summaries are coherent and accurate
4. ✅ Dual-LLM routing works correctly (Claude plans, ChatGPT summarizes)
5. ✅ No unhandled exceptions or server crashes
6. ✅ Browser validation confirms pages exist and are well-structured
7. ✅ Execution completes within 3 minutes
8. ✅ Metrics accurately reflect tool usage

---

## 🚨 Failure Scenarios & Troubleshooting

### If /act returns 500 error:
```bash
# Check API logs
docker logs chad-core-api --tail 100

# Check for missing dependencies
cd /workspace/chad-core && make test

# Verify .env has all required keys
grep -E "OPENAI_API_KEY|ANTHROPIC_API_KEY|NOTION_API_KEY" .env
```

### If LangGraph doesn't execute:
```bash
# Test LangGraph directly
python3 << 'EOF'
import asyncio
from chad_agents.graphs.graph_langgraph import create_knowledge_organization_graph

async def test():
    graph = create_knowledge_organization_graph()
    result = await graph.ainvoke({"goal": "test", "actor": "test"})
    print(result)

asyncio.run(test())
EOF
```

### If Notion API returns 401:
- Verify `NOTION_API_KEY` in .env is valid
- Check Notion integration has page permissions
- Test with direct Notion API call: `curl -H "Authorization: Bearer $NOTION_API_KEY" https://api.notion.com/v1/search`

---

## 📝 Test Report Template

```markdown
# Chad-Core E2E Test Report

**Date**: 2024-11-20
**Tester**: Manus (Browser Agent)
**Duration**: XX minutes
**Result**: PASS / FAIL

## Summary
[Brief overview of test execution]

## Test Results
- Notion Search: PASS / FAIL
- Page Reading: PASS / FAIL
- Agent Workflow: PASS / FAIL
- Browser Validation: PASS / FAIL
- Error Handling: PASS / FAIL

## Issues Found
1. [Issue description]
2. [Issue description]

## Screenshots
- [Link to screenshots]

## Recommendations
- [Improvement suggestions]

## Conclusion
[Final assessment]
```

---

**Manus, execute this comprehensive test suite and report back with results, screenshots, and any issues encountered. Focus especially on Phase 3 (Autonomous Agent Workflow) and Phase 4 (Browser Validation) as these are the core functionality tests.**
