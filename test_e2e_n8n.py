#!/usr/bin/env python3
"""
End-to-End Test: Chad with n8n Workflow Integration

Tests the complete flow:
1. Chad API startup with tool discovery
2. N8n workflow registration from Notion documentation
3. Tool execution through LangGraph
4. Webhook calling with authentication

Note: This test assumes:
- Notion "n8n Workflows" folder exists with "Send Notification" page
- n8n webhook is properly registered and active
- CHAD_ROUTER_TOKEN is set in environment
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")

from chad_tools.registry import ToolRegistry
from chad_tools.adapters.notion import NotionClientWrapper
from chad_tools.adapters.n8n import N8nWorkflowRegistry


async def test_tool_discovery():
    """Test discovering n8n workflows from Notion."""

    print("=" * 70)
    print("Chad E2E Test: n8n Workflow Discovery and Execution")
    print("=" * 70)
    print()

    # Step 1: Initialize components
    print("📦 Step 1: Initializing components...")
    tool_registry = ToolRegistry()
    notion_api_key = os.getenv("NOTION_API_KEY")
    notion_client = NotionClientWrapper(api_key=notion_api_key)
    n8n_api_key = os.getenv("CHAD_ROUTER_TOKEN")

    if not n8n_api_key:
        print("  ⚠️  Warning: CHAD_ROUTER_TOKEN not set in environment")
        print("     Workflows will be discovered but authentication will fail")

    print(f"  ✅ Tool registry initialized")
    print(f"  ✅ Notion client initialized")
    print()

    # Step 2: Discover n8n workflows
    print("🔍 Step 2: Discovering n8n workflows from Notion...")

    n8n_registry = N8nWorkflowRegistry(
        notion_client=notion_client,
        tool_registry=tool_registry,
        api_key=n8n_api_key,
    )

    try:
        workflow_count = await n8n_registry.discover_and_register()
        print(f"  ✅ Discovered and registered {workflow_count} workflow(s)")

        if workflow_count == 0:
            print()
            print("  ℹ️  No workflows found. This is expected if:")
            print("     1. 'n8n Workflows' folder doesn't exist in Notion yet")
            print("     2. The folder exists but has no child pages")
            print()
            print("  To fix:")
            print("     1. Create 'n8n Workflows' folder in Notion")
            print("     2. Add workflow documentation pages as child pages")
            print("     3. See: /workspace/File_uploads_CC/Notion_Workflow_Documentation.md")
            print()
            return False

    except Exception as e:
        print(f"  ❌ Discovery failed: {e}")
        print()
        print("  Common causes:")
        print("     1. NOTION_API_KEY not set or invalid")
        print("     2. 'n8n Workflows' folder doesn't exist")
        print("     3. Notion API connection issue")
        print()
        return False

    print()

    # Step 3: List discovered tools
    print("📋 Step 3: Registered tools:")
    print(f"  Total tools: {len(tool_registry._tools)}")

    for tool_name in sorted(tool_registry._tools.keys()):
        tool = tool_registry.get(tool_name)
        print(f"    • {tool_name}")
        if hasattr(tool, "workflow_metadata"):
            print(f"      URL: {tool.workflow_metadata.webhook_url}")
            print(f"      Capabilities: {', '.join(tool.metadata.capabilities)}")

    print()

    # Step 4: Test workflow execution (dry-run)
    print("🧪 Step 4: Testing workflow execution (dry-run)...")

    n8n_tools = [
        name for name in tool_registry._tools.keys() if name.startswith("n8n_")
    ]

    if not n8n_tools:
        print("  ⚠️  No n8n tools registered to test")
        return True

    # Test the first n8n tool
    test_tool_name = n8n_tools[0]
    test_tool = tool_registry.get(test_tool_name)

    print(f"  Testing tool: {test_tool_name}")
    print(f"  Description: {test_tool.description}")

    # Execute in dry-run mode
    result = await test_tool.execute(
        ctx={"dry_run": True, "actor": "test_user"},
        input_data={
            "message": "Test notification from E2E test",
            "channels": ["slack", "email"],
        },
    )

    print(f"  Status: {result['status']}")
    print(f"  Message: {result.get('message', 'N/A')}")
    print()

    # Step 5: Test real workflow execution (if webhook is registered)
    if os.getenv("TEST_REAL_WEBHOOK", "false").lower() == "true":
        print("🚀 Step 5: Testing REAL workflow execution...")
        print("  (Set TEST_REAL_WEBHOOK=false to skip this)")
        print()

        real_result = await test_tool.execute(
            ctx={"dry_run": False, "actor": "test_user"},
            input_data={
                "message": "Real test notification from Chad E2E test",
                "channels": ["slack"],
                "priority": "normal",
                "metadata": {"test": True, "source": "e2e_test"},
            },
        )

        print(f"  Status: {real_result['status']}")

        if real_result["status"] == "success":
            print(f"  ✅ Workflow executed successfully!")
            if real_result.get("data"):
                print(f"  Response: {real_result['data']}")
        else:
            print(f"  ❌ Workflow execution failed:")
            print(f"     {real_result.get('error')}")

        print()
    else:
        print("⏭️  Step 5: Skipping real workflow execution")
        print("   (Set TEST_REAL_WEBHOOK=true to enable)")
        print()

    # Cleanup (NotionClientWrapper doesn't need explicit close)
    # await notion_client.close()

    print("=" * 70)
    print("✅ TEST COMPLETE")
    print("=" * 70)
    print()

    return True


async def test_tool_list_endpoint():
    """Test listing available tools (simulates GET /tools endpoint)."""

    print("\n" + "=" * 70)
    print("Bonus Test: Tool Listing")
    print("=" * 70)
    print()

    tool_registry = ToolRegistry()
    notion_api_key = os.getenv("NOTION_API_KEY")
    notion_client = NotionClientWrapper(api_key=notion_api_key)
    n8n_api_key = os.getenv("CHAD_ROUTER_TOKEN")

    # Register tools
    n8n_registry = N8nWorkflowRegistry(
        notion_client=notion_client,
        tool_registry=tool_registry,
        api_key=n8n_api_key,
    )

    try:
        await n8n_registry.discover_and_register()
    except Exception:
        pass

    # List all tools with metadata
    print("📋 Available Chad Tools:\n")

    for tool_name in sorted(tool_registry._tools.keys()):
        tool = tool_registry.get(tool_name)
        print(f"  🔧 {tool_name}")
        print(f"     Description: {tool.description}")
        print(f"     Risk Level: {tool.metadata.risk_level}")
        print(f"     Dry-run: {tool.metadata.dry_run_supported}")
        print(f"     Capabilities: {', '.join(tool.metadata.capabilities) or 'none'}")
        print()

    # NotionClientWrapper doesn't need explicit close
    # await notion_client.close()


if __name__ == "__main__":
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║         CHAD-CORE: N8N WORKFLOW INTEGRATION TEST                  ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print()

    success = asyncio.run(test_tool_discovery())

    if success:
        asyncio.run(test_tool_list_endpoint())

    print("\n" + ("🎉 ALL TESTS PASSED!" if success else "❌ TESTS FAILED"))
    print()
