#!/usr/bin/env python3
"""Test Notion adapter with real Notion workspace.

Requirements:
- Notion integration token (internal integration)
- At least one page in your Notion workspace

Setup:
1. Go to https://www.notion.so/my-integrations
2. Create a new integration
3. Copy the "Internal Integration Token"
4. Add to .env: NOTION_API_KEY=secret_...
5. Share a page with your integration
6. Run this script
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

from chad_tools.adapters.notion import (
    NotionSearchTool,
    NotionReadPageTool,
    NotionCreatePageTool,
    NotionQueryDatabaseTool,
)


def check_api_key():
    """Check if NOTION_API_KEY is set."""
    api_key = os.getenv("NOTION_API_KEY")

    if not api_key:
        print("❌ Error: NOTION_API_KEY not found in environment")
        print("")
        print("Setup Instructions:")
        print("1. Go to https://www.notion.so/my-integrations")
        print("2. Click '+ New integration'")
        print("3. Give it a name (e.g., 'Chad-Core Integration')")
        print("4. Select your workspace")
        print("5. Copy the 'Internal Integration Token'")
        print("6. Add to .env file: NOTION_API_KEY=secret_...")
        print("7. Share at least one page with the integration")
        print("")
        return None

    if api_key.startswith("secret_placeholder"):
        print("❌ Error: Using placeholder API key")
        print("Please replace with your real Notion integration token")
        return None

    # Accept both old (secret_) and new (ntn_) Notion key formats
    if not (api_key.startswith("secret_") or api_key.startswith("ntn_")):
        print("⚠️  Warning: API key should start with 'secret_' or 'ntn_'")
        print(f"   Your key starts with: {api_key[:10]}...")

    print(f"✅ API key found: {api_key[:15]}...")
    return api_key


async def test_search(api_key: str):
    """Test NotionSearchTool with real API."""
    print("\n" + "="*60)
    print("🔍 Testing NotionSearchTool")
    print("="*60)

    tool = NotionSearchTool(api_key=api_key)

    try:
        # Search for any pages (empty query returns all)
        result = await tool.execute(
            ctx={"actor": "test_user"},
            input_data={"query": "", "max_results": 5}
        )

        print(f"✅ Search successful!")
        print(f"   Status: {result['status']}")
        print(f"   Total results: {result['total_count']}")
        print(f"   Has more: {result['has_more']}")
        print("")

        if result['total_count'] == 0:
            print("⚠️  No pages found!")
            print("   Make sure you've shared at least one page with your integration:")
            print("   1. Open a page in Notion")
            print("   2. Click '...' menu → 'Add connections'")
            print("   3. Select your integration")
            return None

        print("📄 Found pages:")
        for i, page in enumerate(result['results'][:5], 1):
            print(f"   {i}. {page['title']}")
            print(f"      Type: {page['type']}")
            print(f"      ID: {page['id']}")
            print(f"      URL: {page['url']}")
            print(f"      Parent: {page['parent_type']}")
            print("")

        return result['results'][0] if result['results'] else None

    except Exception as e:
        print(f"❌ Search failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return None


async def test_read_page(api_key: str, page_id: str):
    """Test NotionReadPageTool with real API."""
    print("\n" + "="*60)
    print("📖 Testing NotionReadPageTool")
    print("="*60)

    tool = NotionReadPageTool(api_key=api_key)

    try:
        result = await tool.execute(
            ctx={"actor": "test_user"},
            input_data={"page_id": page_id}
        )

        print(f"✅ Read page successful!")
        print(f"   Status: {result['status']}")
        print(f"   Title: {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   Content blocks: {len(result['content'])}")
        print(f"   Markdown length: {len(result['markdown'])} chars")
        print(f"   Created: {result['created_time']}")
        print(f"   Last edited: {result['last_edited_time']}")
        print("")

        print("📝 Markdown preview (first 500 chars):")
        print("-" * 60)
        print(result['markdown'][:500])
        if len(result['markdown']) > 500:
            print(f"... ({len(result['markdown']) - 500} more chars)")
        print("-" * 60)
        print("")

        print("🧱 Block structure:")
        for i, block in enumerate(result['content'][:10], 1):
            print(f"   {i}. {block['type']}: {block['content'][:50]}...")
            if len(result['content']) > 10 and i == 10:
                print(f"   ... ({len(result['content']) - 10} more blocks)")
                break

        return result

    except Exception as e:
        print(f"❌ Read page failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return None


async def test_create_page_dry_run(api_key: str):
    """Test NotionCreatePageTool in dry-run mode."""
    print("\n" + "="*60)
    print("✏️  Testing NotionCreatePageTool (DRY-RUN)")
    print("="*60)

    tool = NotionCreatePageTool(api_key=api_key)

    try:
        result = await tool.execute(
            ctx={"actor": "test_user"},
            input_data={
                "parent_id": "workspace",
                "title": "Chad-Core Test Page",
                "content_markdown": """
# Chad-Core Integration Test

This page was created by the Chad-Core Notion adapter test.

## Features Tested
- Search functionality ✅
- Read page content ✅
- Create page (dry-run) ✅

## Next Steps
- Test with real page creation
- Query databases
- Build agent workflows
                """,
                "icon_emoji": "🤖",
                "dry_run": True  # Safe - doesn't actually create
            }
        )

        print(f"✅ Create page dry-run successful!")
        print(f"   Status: {result['status']}")
        print(f"   Title: {result['title']}")
        print(f"   Would create URL: {result['url']}")
        print("")

        if "preview" in result:
            preview = result["preview"]
            print("📋 Preview:")
            print(f"   Title: {preview['title']}")
            print(f"   Content length: {preview['content_length']} chars")
            print(f"   Icon: {preview['icon']}")
            print(f"   Parent type: {preview['parent_type']}")

        print("")
        print("ℹ️  This was a dry-run - no page was actually created")
        print("   To create a real page, set dry_run=False and provide a real parent_id")

        return result

    except Exception as e:
        print(f"❌ Create page dry-run failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return None


async def test_query_database_dry_run(api_key: str):
    """Test NotionQueryDatabaseTool in dry-run mode."""
    print("\n" + "="*60)
    print("🗄️  Testing NotionQueryDatabaseTool (DRY-RUN)")
    print("="*60)

    tool = NotionQueryDatabaseTool(api_key=api_key)

    try:
        result = await tool.execute(
            ctx={"actor": "test_user"},
            input_data={
                "database_id": "mock-database-id",
                "dry_run": True  # Safe - doesn't query real database
            }
        )

        print(f"✅ Query database dry-run successful!")
        print(f"   Status: {result['status']}")
        print(f"   Mock results: {result['total_count']}")
        print("")

        if result['results']:
            print("📊 Mock database entry:")
            entry = result['results'][0]
            print(f"   Page ID: {entry['page_id']}")
            print(f"   URL: {entry['url']}")
            print(f"   Properties:")
            for key, value in entry['properties'].items():
                print(f"      {key}: {value}")

        print("")
        print("ℹ️  This was a dry-run - no real database was queried")
        print("   To query a real database, set dry_run=False and provide a real database_id")

        return result

    except Exception as e:
        print(f"❌ Query database dry-run failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return None


async def main():
    """Run all tests with real Notion workspace."""
    print("="*60)
    print("🤖 Chad-Core Notion Adapter - Real Workspace Test")
    print("="*60)

    # Check API key
    api_key = check_api_key()
    if not api_key:
        sys.exit(1)

    # Test search
    first_page = await test_search(api_key)

    if not first_page:
        print("\n⚠️  Cannot continue - no pages accessible")
        print("   Make sure you've shared pages with your integration")
        return

    # Test read page (only if it's a page, not a database)
    if first_page['type'] == 'page':
        await test_read_page(api_key, first_page['id'])
    else:
        print(f"\n⚠️  First result is a database, skipping read page test")
        print(f"   To test reading, share a regular page with your integration")

    # Test create page (dry-run only)
    await test_create_page_dry_run(api_key)

    # Test query database (dry-run only)
    await test_query_database_dry_run(api_key)

    # Summary
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60)
    print("")
    print("🎉 Your Notion integration is working!")
    print("")
    print("Next steps:")
    print("1. Try searching with a specific query")
    print("2. Test creating a real page (remove dry_run=True)")
    print("3. Query a real database (get database_id from URL)")
    print("4. Integrate with LangGraph agent loop")
    print("5. Build knowledge-base workflows")
    print("")


if __name__ == "__main__":
    asyncio.run(main())
