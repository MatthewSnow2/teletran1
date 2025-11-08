#!/usr/bin/env python3
"""
End-to-End Test for Chad-Core

Tests the complete workflow:
1. Initialize LLM Router (GPT-5 + Claude Sonnet 4.5)
2. Initialize Tool Registry (Notion tools)
3. Execute agent workflow via execute_agent_loop
4. Verify results

This test uses REAL API calls to OpenAI and Anthropic.
Ensure OPENAI_API_KEY and ANTHROPIC_API_KEY are set in .env
"""

import asyncio
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from chad_llm import LLMRouter
from chad_tools.registry import ToolRegistry
from chad_agents.graphs.graph_langgraph import execute_agent_loop


async def test_simple_goal():
    """Test a simple goal: Find pages in Notion workspace."""

    print("=" * 70)
    print("Chad-Core E2E Test: Simple Goal")
    print("=" * 70)
    print()

    # Step 1: Initialize components
    print("📦 Initializing components...")
    try:
        llm_router = LLMRouter()
        print(f"  ✅ LLM Router initialized")
        print(f"     - ChatGPT: {llm_router.chatgpt.model_name}")
        print(f"     - Claude: {llm_router.claude.model_name}")
    except Exception as e:
        print(f"  ❌ LLM Router failed: {e}")
        return False

    try:
        tool_registry = ToolRegistry()
        print(f"  ✅ Tool Registry initialized")
        print(f"     - Tools available: {len(tool_registry._tools)}")
    except Exception as e:
        print(f"  ❌ Tool Registry failed: {e}")
        return False

    print()

    # Step 2: Define simple test goal
    print("🎯 Goal: Find all pages in my Notion workspace")
    print()

    run_id = "test-run-001"
    goal = "Search my Notion workspace and tell me what pages you find"
    context = {"actor": "test_user"}

    # Step 3: Execute workflow
    print("🚀 Executing agent workflow...")
    print()

    try:
        result = await execute_agent_loop(
            run_id=run_id,
            goal=goal,
            context=context,
            autonomy_level="L2",  # ExecuteNotify
            dry_run=False,
            max_steps=3,  # Keep it simple: plan, search, reflect
            llm_router=llm_router,
            tool_registry=tool_registry,
        )

        print("=" * 70)
        print("✅ EXECUTION COMPLETE")
        print("=" * 70)
        print()

        # Step 4: Display results
        print("📊 RESULTS:")
        print(f"  Status: {result.get('status')}")
        print(f"  Steps Executed: {result.get('steps_executed', 0)}")
        print(f"  LLM Calls: {result.get('llm_calls', 0)}")
        print(f"  Artifacts Created: {len(result.get('artifacts', []))}")
        print()

        if result.get('notification'):
            print("💬 User Notification:")
            print(f"  {result.get('notification')}")
            print()

        # Display executed steps
        if 'executed_steps' in result:
            print("📝 Execution Steps:")
            for i, step in enumerate(result['executed_steps'], 1):
                status = step.get('status', 'unknown')
                tool = step.get('tool', 'unknown')
                print(f"  {i}. [{status.upper()}] {tool}")
                if step.get('error'):
                    print(f"     Error: {step.get('error')}")
            print()

        # Display plan
        if result.get('plan'):
            print("📋 Generated Plan:")
            for i, step in enumerate(result['plan'], 1):
                print(f"  {i}. {step.get('tool', 'unknown')}")
                print(f"     Purpose: {step.get('purpose', 'N/A')}")
            print()

        print("=" * 70)

        return result.get('status') == 'completed'

    except Exception as e:
        print(f"❌ Execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_llm_routing():
    """Test that LLM routing works correctly."""

    print("=" * 70)
    print("Chad-Core E2E Test: LLM Routing")
    print("=" * 70)
    print()

    try:
        llm_router = LLMRouter()

        # Test 1: Planning task (should route to Claude)
        print("🧪 Test 1: Planning Task (should use Claude)")
        response, model = await llm_router.generate(
            prompt="Create a simple 2-step plan to search Notion for pages about AI",
            temperature=0.3,
            max_tokens=500,
        )
        print(f"  ✅ Response from: {model}")
        print(f"  📝 Response preview: {response[:100]}...")
        assert "claude" in model.lower(), f"Expected Claude, got {model}"
        print()

        # Test 2: User response (should route to ChatGPT)
        print("🧪 Test 2: User Notification (should use ChatGPT/GPT-5)")
        from chad_llm.router import TaskType
        response, model = await llm_router.generate(
            prompt="Write a friendly message saying the task is complete",
            task_type=TaskType.USER_RESPONSE,
            temperature=0.7,
            max_tokens=200,
        )
        print(f"  ✅ Response from: {model}")
        print(f"  📝 Response preview: {response[:100]}...")
        assert "gpt" in model.lower(), f"Expected GPT, got {model}"
        print()

        print("=" * 70)
        print("✅ LLM ROUTING TEST PASSED")
        print("=" * 70)
        print()

        return True

    except Exception as e:
        print(f"❌ LLM Routing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all E2E tests."""

    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "CHAD-CORE END-TO-END TESTS" + " " * 27 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    print("Models:")
    print("  🤖 GPT-5 (gpt-5-2025-08-07)")
    print("  🤖 Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)")
    print()

    # Run tests
    results = []

    # Test 1: LLM Routing
    print()
    results.append(("LLM Routing", await test_llm_routing()))

    # Test 2: Simple Goal
    print()
    results.append(("Simple Goal Execution", await test_simple_goal()))

    # Summary
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
    print()

    all_passed = all(passed for _, passed in results)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED")
    print()

    return all_passed


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
