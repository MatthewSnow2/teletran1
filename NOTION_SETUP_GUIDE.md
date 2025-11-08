# Notion Integration Setup Guide

**Goal**: Connect Chad-Core to your Notion workspace for testing

---

## Step 1: Create a Notion Integration

1. **Go to Notion Integrations page**:
   - Visit: https://www.notion.so/my-integrations
   - Log in to your Notion account

2. **Create a new integration**:
   - Click **"+ New integration"**
   - Give it a name: `Chad-Core Integration`
   - Select your workspace
   - Click **"Submit"**

3. **Copy the API key**:
   - You'll see **"Internal Integration Token"**
   - Click **"Show"** then **"Copy"**
   - It will look like: `secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

4. **Set capabilities** (default is fine):
   - ✅ Read content
   - ✅ Update content
   - ✅ Insert content

---

## Step 2: Add API Key to .env

1. **Open your .env file**:
   ```bash
   nano .env
   # or use your preferred editor
   ```

2. **Update the NOTION_API_KEY line**:
   ```bash
   # Replace this:
   NOTION_API_KEY=secret_placeholder_will_add_real_key_later

   # With your actual key:
   NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

3. **Save the file**

---

## Step 3: Share Pages with the Integration

**IMPORTANT**: Your integration can only access pages you explicitly share with it.

### Option A: Share a Specific Page

1. Open a page in Notion
2. Click the **"..."** menu (top right)
3. Click **"Add connections"**
4. Select **"Chad-Core Integration"**
5. The integration can now access this page and its children

### Option B: Share Your Entire Workspace (Not Recommended)

1. Go to Settings & Members → Connections
2. Add your integration to the workspace
3. All pages will be accessible

**Recommendation**: Start by sharing just 1-2 test pages.

---

## Step 4: Run the Test

```bash
python3 test_real_notion.py
```

Expected output:
```
============================================================
🤖 Chad-Core Notion Adapter - Real Workspace Test
============================================================
✅ API key found: secret_xxxxxxx...

============================================================
🔍 Testing NotionSearchTool
============================================================
✅ Search successful!
   Status: success
   Total results: 5
   Has more: False

📄 Found pages:
   1. My First Page
      Type: page
      ID: abc-123-def-456
      URL: https://notion.so/My-First-Page-abc123
      Parent: workspace

...
```

---

## Troubleshooting

### ❌ "No pages found!"

**Problem**: The integration can't see any pages.

**Solution**:
1. Make sure you shared at least one page with the integration
2. Try sharing a page with content (not empty)
3. Wait a few seconds and try again

---

### ❌ "Authentication failed: unauthorized"

**Problem**: Invalid API key.

**Solution**:
1. Check that the API key starts with `secret_`
2. Make sure you copied the entire key
3. Regenerate the key in Notion integrations page
4. Update .env with the new key

---

### ❌ "Rate limit exceeded"

**Problem**: Too many requests in a short time.

**Solution**:
- Wait 1 minute and try again
- The adapter has built-in rate limiting (3 req/s)
- For production, consider caching

---

## What You Can Test

### 1. Search Your Workspace

```python
from chad_tools.adapters.notion import NotionSearchTool
import os

tool = NotionSearchTool(api_key=os.getenv("NOTION_API_KEY"))
result = await tool.execute(
    ctx={"actor": "user"},
    input_data={"query": "meeting notes", "max_results": 10}
)
```

### 2. Read a Page as Markdown

```python
from chad_tools.adapters.notion import NotionReadPageTool

tool = NotionReadPageTool(api_key=os.getenv("NOTION_API_KEY"))
result = await tool.execute(
    ctx={"actor": "user"},
    input_data={"page_id": "your-page-id-here"}
)

print(result["markdown"])
```

### 3. Create a New Page

```python
from chad_tools.adapters.notion import NotionCreatePageTool

tool = NotionCreatePageTool(api_key=os.getenv("NOTION_API_KEY"))
result = await tool.execute(
    ctx={"actor": "user"},
    input_data={
        "parent_id": "parent-page-id",  # Get from search results
        "parent_type": "page_id",
        "title": "Created by Chad-Core",
        "content_markdown": "# Hello from Chad!\n\nThis page was created programmatically.",
        "icon_emoji": "🤖"
    }
)
```

### 4. Query a Database

```python
from chad_tools.adapters.notion import NotionQueryDatabaseTool

tool = NotionQueryDatabaseTool(api_key=os.getenv("NOTION_API_KEY"))
result = await tool.execute(
    ctx={"actor": "user"},
    input_data={
        "database_id": "your-database-id",  # From database URL
        "filter_conditions": {
            "property": "Status",
            "select": {"equals": "In Progress"}
        }
    }
)
```

---

## Getting Page/Database IDs

### From URL

**Page URL**:
```
https://notion.so/My-Page-abc123def456
                            ^^^^^^^^^^ This is the page ID
```

**Database URL**:
```
https://notion.so/abc123def456?v=xyz789
              ^^^^^^^^^^ This is the database ID
```

### From Search Results

```python
result = await search_tool.execute(
    ctx={"actor": "user"},
    input_data={"query": "My Page"}
)

page_id = result["results"][0]["id"]
```

---

## Security Best Practices

1. **Never commit your .env file**:
   - It's already in `.gitignore`
   - Keep your API key secret

2. **Rotate keys regularly**:
   - Generate a new integration token every 90 days
   - Update .env with new key

3. **Limit permissions**:
   - Only share pages that the integration needs
   - Remove access when not needed

4. **Use read-only for testing**:
   - Start with search and read operations
   - Test create operations with dry_run=True first

---

## Next Steps

Once you verify the connection works:

1. **Build agent workflows**:
   - Search knowledge base
   - Read and summarize pages
   - Create summary pages

2. **Integrate with LangGraph**:
   - Plan → Search → Read → Summarize → Create
   - Full autonomous knowledge workflows

3. **Add caching**:
   - Cache search results (5 min TTL)
   - Cache page content (1 hour TTL)

4. **Create specialized tools**:
   - Update existing pages
   - Append to pages
   - Database-specific queries

---

## Support

If you encounter issues:

1. Check the error message carefully
2. Review Notion API documentation: https://developers.notion.com
3. Verify integration permissions
4. Check that pages are shared with the integration

---

**Ready to test? Run `python3 test_real_notion.py`** 🚀
