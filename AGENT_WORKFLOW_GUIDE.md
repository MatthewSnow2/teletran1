# Agent Workflow & LangGraph Integration Guide

**Purpose**: Understand how to build autonomous knowledge workflows using Chad-Core's Notion integration

---

## Overview: The Agent Workflow Vision

Chad-Core is designed to act as an autonomous knowledge agent that can:
1. **Search** your Notion workspace for relevant information
2. **Read** and understand page content
3. **Summarize** or process information using LLMs
4. **Create** new knowledge pages with insights

This creates a **self-improving knowledge base** where Chad continuously organizes and synthesizes information.

---

## Step 3: Agent Workflows (search → read → summarize → create)

### What is an Agent Workflow?

An **agent workflow** is a multi-step autonomous process where an AI agent:
- Receives a **goal** (e.g., "Summarize all meeting notes from this week")
- **Plans** the steps needed (search, read, summarize, create)
- **Executes** tools to accomplish each step
- **Reflects** on results and adjusts the plan
- **Delivers** a final outcome

### Example Workflow: Weekly Meeting Summary

**User Goal**: "Create a weekly summary of all meeting notes"

**Agent Plan**:
```
1. Search Notion for pages with "meeting" in title
2. Filter results to last 7 days
3. Read each meeting note page
4. Extract key decisions and action items
5. Summarize with LLM
6. Create new "Weekly Summary" page
7. Return URL of created page
```

**Chad-Core Execution**:
```python
# Step 1: Search
search_result = await notion_search_tool.execute(
    ctx={"actor": "user_123"},
    input_data={"query": "meeting notes", "max_results": 20}
)

# Step 2: Read each page
meeting_contents = []
for page in search_result["results"]:
    if page["type"] == "page":
        content = await notion_read_page_tool.execute(
            ctx={"actor": "user_123"},
            input_data={"page_id": page["id"]}
        )
        meeting_contents.append({
            "title": content["title"],
            "markdown": content["markdown"],
            "date": content["last_edited_time"]
        })

# Step 3: Summarize with LLM (TODO: implement)
summary_prompt = f"""
Summarize these meeting notes from the past week:

{chr(10).join([f"## {m['title']}\n{m['markdown']}" for m in meeting_contents])}

Extract:
- Key decisions made
- Action items assigned
- Important discussions
"""

summary = await llm.generate(summary_prompt)  # TODO: LLM integration

# Step 4: Create summary page
create_result = await notion_create_page_tool.execute(
    ctx={"actor": "user_123"},
    input_data={
        "parent_id": "workspace_root",
        "title": f"Weekly Summary - {datetime.now().strftime('%Y-%m-%d')}",
        "content_markdown": summary,
        "icon_emoji": "📊"
    }
)

return f"Summary created: {create_result['url']}"
```

### Workflow Patterns

#### Pattern 1: Knowledge Discovery
**Goal**: Find and organize related information
```
Search → Read → Categorize → Create Index Page
```

#### Pattern 2: Content Synthesis
**Goal**: Combine multiple sources into insights
```
Search → Read Multiple → Analyze → Create Summary
```

#### Pattern 3: Knowledge Validation
**Goal**: Check facts and update outdated info
```
Search → Read → Verify with External Sources → Update/Flag
```

#### Pattern 4: Proactive Monitoring
**Goal**: Watch for changes and notify
```
Search (Periodic) → Compare with Previous → Notify if Changed
```

---

## Step 4: LangGraph Integration for Autonomous Execution

### What is LangGraph?

**LangGraph** is a library for building **stateful, multi-agent workflows** with LLMs. It provides:
- **Nodes**: Individual steps (tools, LLM calls, logic)
- **Edges**: Connections between steps (conditional routing)
- **State**: Shared context passed between nodes
- **Cycles**: Ability to loop and reflect

### Why LangGraph for Chad-Core?

Chad-Core uses LangGraph to implement the **plan → tool → reflect** pattern:

1. **Planning Node**: LLM creates execution plan
2. **Tool Node**: Execute Notion tools
3. **Reflection Node**: Check if goal is achieved
4. **Loop**: Repeat until goal met or max steps reached

### LangGraph Architecture in Chad-Core

```python
# chad_agents/graphs/graph_langgraph.py (currently a stub)

from langgraph.graph import Graph, StateGraph
from langchain_core.messages import HumanMessage, AIMessage

# Define state schema
class AgentState(TypedDict):
    goal: str                    # User's goal
    actor: str                   # Who initiated
    plan: list[dict]             # Planned steps
    executed_steps: list[dict]   # Completed steps
    current_step: int            # Step index
    working_memory: dict         # Temporary data
    final_result: dict | None    # Final output
    messages: list               # LLM conversation history

# Define the graph
def create_agent_graph(tools: list) -> Graph:
    """Create LangGraph execution graph."""

    graph = StateGraph(AgentState)

    # Node 1: Planning
    graph.add_node("plan", plan_node)

    # Node 2: Execute tool
    graph.add_node("execute_tool", execute_tool_node)

    # Node 3: Reflect on result
    graph.add_node("reflect", reflect_node)

    # Node 4: Finalize
    graph.add_node("finalize", finalize_node)

    # Edges
    graph.set_entry_point("plan")
    graph.add_edge("plan", "execute_tool")
    graph.add_conditional_edges(
        "execute_tool",
        should_continue,  # Function that decides next step
        {
            "continue": "reflect",
            "done": "finalize"
        }
    )
    graph.add_conditional_edges(
        "reflect",
        check_goal_achieved,
        {
            "achieved": "finalize",
            "continue": "execute_tool",
            "replan": "plan"
        }
    )
    graph.set_finish_point("finalize")

    return graph.compile()
```

### Node Implementations

#### Planning Node
```python
async def plan_node(state: AgentState) -> AgentState:
    """Generate execution plan using LLM."""

    # Build prompt for LLM
    prompt = f"""
You are Chad, an autonomous knowledge agent with access to Notion.

Goal: {state['goal']}

Available Tools:
- notion.search: Search workspace for pages/databases
- notion.pages.read: Read full page content as markdown
- notion.pages.create: Create new pages
- notion.databases.query: Query databases with filters

Create a step-by-step plan to achieve the goal. For each step:
1. Specify which tool to use
2. Define the inputs needed
3. Explain what the step accomplishes

Output as JSON:
{{
  "steps": [
    {{"tool": "notion.search", "input": {{"query": "...", "max_results": 5}}, "purpose": "..."}},
    {{"tool": "notion.pages.read", "input": {{"page_id": "{{from_step_1}}"}}, "purpose": "..."}}
  ]
}}
"""

    # Call LLM (TODO: implement LLM integration)
    response = await llm.generate(prompt)
    plan = json.loads(response)

    state["plan"] = plan["steps"]
    state["current_step"] = 0

    return state
```

#### Execute Tool Node
```python
async def execute_tool_node(state: AgentState) -> AgentState:
    """Execute the current step's tool."""

    current_step = state["plan"][state["current_step"]]
    tool_name = current_step["tool"]
    tool_input = current_step["input"]

    # Get tool from registry
    tool = tool_registry.get(tool_name)

    # Execute tool
    try:
        result = await tool.execute(
            ctx={"actor": state["actor"]},
            input_data=tool_input
        )

        # Store result
        state["executed_steps"].append({
            "step": state["current_step"],
            "tool": tool_name,
            "input": tool_input,
            "output": result,
            "status": "success"
        })

        # Store in working memory for next steps
        state["working_memory"][f"step_{state['current_step']}_result"] = result

        state["current_step"] += 1

    except Exception as e:
        state["executed_steps"].append({
            "step": state["current_step"],
            "tool": tool_name,
            "input": tool_input,
            "error": str(e),
            "status": "failed"
        })

    return state
```

#### Reflection Node
```python
async def reflect_node(state: AgentState) -> AgentState:
    """Reflect on progress and decide next action."""

    # Build reflection prompt
    prompt = f"""
Goal: {state['goal']}

Executed Steps:
{json.dumps(state['executed_steps'], indent=2)}

Working Memory:
{json.dumps(state['working_memory'], indent=2)}

Analyze:
1. Has the goal been achieved?
2. Should we continue with the plan?
3. Do we need to replan based on results?

Output as JSON:
{{
  "goal_achieved": true/false,
  "next_action": "continue" | "achieved" | "replan",
  "reasoning": "..."
}}
"""

    response = await llm.generate(prompt)
    reflection = json.loads(response)

    state["messages"].append(AIMessage(content=reflection["reasoning"]))

    return state
```

### Conditional Routing Functions

```python
def should_continue(state: AgentState) -> str:
    """Decide if execution should continue."""
    if state["current_step"] >= len(state["plan"]):
        return "done"  # All steps executed
    return "continue"

def check_goal_achieved(state: AgentState) -> str:
    """Check reflection result."""
    last_message = state["messages"][-1]
    reflection = json.loads(last_message.content)

    if reflection["goal_achieved"]:
        return "achieved"
    elif reflection["next_action"] == "replan":
        return "replan"
    else:
        return "continue"
```

---

## Complete Example: Knowledge Summary Workflow

### Scenario
**Goal**: "Create a summary of all Python-related pages in my Notion workspace"

### Step-by-Step Execution

#### 1. User Request
```python
from apps.core_api.routers.act import execute_agent_workflow

result = await execute_agent_workflow(
    actor="user_123",
    goal="Create a summary of all Python-related pages in my Notion workspace",
    context={},
    max_steps=10
)
```

#### 2. LangGraph Planning (Node 1)
```json
{
  "steps": [
    {
      "tool": "notion.search",
      "input": {"query": "Python", "max_results": 10},
      "purpose": "Find all Python-related pages"
    },
    {
      "tool": "notion.pages.read",
      "input": {"page_id": "{{from_search}}"},
      "purpose": "Read each page content",
      "iterate": true
    },
    {
      "tool": "llm.summarize",
      "input": {"content": "{{aggregated_content}}"},
      "purpose": "Generate summary"
    },
    {
      "tool": "notion.pages.create",
      "input": {
        "parent_id": "workspace",
        "title": "Python Knowledge Summary",
        "content_markdown": "{{from_summarize}}"
      },
      "purpose": "Create summary page"
    }
  ]
}
```

#### 3. Execution Loop (Nodes 2-3)

**Step 1: Search**
```python
# Execute
result_1 = await notion_search_tool.execute(...)
# Returns: 8 Python-related pages

# Reflect
# Goal not yet achieved, continue to step 2
```

**Step 2: Read Pages (Iterative)**
```python
# Execute for each page
pages_content = []
for page in result_1["results"]:
    if page["type"] == "page":
        content = await notion_read_page_tool.execute(
            input_data={"page_id": page["id"]}
        )
        pages_content.append(content["markdown"])

# Reflect
# Have all content, continue to step 3
```

**Step 3: Summarize with LLM**
```python
# Execute
summary = await llm.generate(
    prompt=f"Summarize these Python pages: {pages_content}"
)

# Reflect
# Summary generated, continue to step 4
```

**Step 4: Create Summary Page**
```python
# Execute
create_result = await notion_create_page_tool.execute(
    input_data={
        "title": "Python Knowledge Summary",
        "content_markdown": summary
    }
)

# Reflect
# Goal achieved! Summary page created at {url}
```

#### 4. Finalization (Node 4)
```python
final_result = {
    "status": "completed",
    "run_id": "550e8400-...",
    "steps_executed": 4,
    "artifacts": [
        {
            "type": "notion_page",
            "url": create_result["url"],
            "title": "Python Knowledge Summary"
        }
    ],
    "message": "Created summary page with 8 Python-related pages"
}
```

---

## What Needs to be Implemented

To make this work, we need to implement:

### 1. LLM Integration
```python
# chad_agents/llm/client.py (NEW FILE)

from anthropic import AsyncAnthropic
# or from openai import AsyncOpenAI

class LLMClient:
    """LLM client for Chad-Core."""

    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate completion from LLM."""
        # TODO: Implement with Claude/GPT-4
        pass

    async def generate_json(self, prompt: str, schema: dict) -> dict:
        """Generate structured JSON output."""
        # TODO: Implement with function calling
        pass
```

### 2. Agent Graph Logic
```python
# chad_agents/graphs/graph_langgraph.py (EXPAND STUB)

# Implement all node functions:
- plan_node()
- execute_tool_node()
- reflect_node()
- finalize_node()

# Implement routing functions:
- should_continue()
- check_goal_achieved()
```

### 3. Working Memory
```python
# chad_memory/stores.py (EXPAND STUB)

class WorkingMemoryStore:
    """Redis-backed working memory for agent execution."""

    async def store_step_result(self, run_id: str, step: int, result: dict):
        """Store step result in Redis."""
        pass

    async def get_context(self, run_id: str) -> dict:
        """Get full execution context."""
        pass
```

### 4. API Integration
```python
# apps/core_api/routers/act.py (EXPAND)

@router.post("/act")
async def act_endpoint(request: ActRequest):
    """Execute agent workflow."""

    # 1. Validate actor permissions
    # 2. Initialize LangGraph
    # 3. Execute graph
    # 4. Return results

    # Currently returns stub response
    # TODO: Integrate with LangGraph execution
```

---

## Autonomy Levels in Workflows

Remember Chad-Core's autonomy system:

### L0 (Ask) - Approval Before Each Tool
```
Plan: [search, read, create]
↓
User approves "search" → Execute → Return result
User approves "read" → Execute → Return result
User approves "create" → Execute → Return result
```

### L1 (Draft) - Dry-Run Plan Approval
```
Plan: [search, read, create]
↓
Execute ALL with dry_run=True → Show preview
User approves entire plan
↓
Re-execute with dry_run=False → Return results
```

### L2 (ExecuteNotify) - Autonomous with Notification
```
Plan: [search, read, create]
↓
Execute all steps automatically
↓
Notify user when complete: "Created summary at {url}"
```

### L3 (ExecuteSilent) - Fully Autonomous
```
Plan: [search, read, create]
↓
Execute silently
↓
Log to audit trail only (no notification)
```

---

## Next Steps to Build This

### Phase 3A: LLM Integration
1. Choose LLM provider (Anthropic Claude, OpenAI GPT-4)
2. Implement `LLMClient` wrapper
3. Add function calling support for structured output
4. Test with simple prompts

### Phase 3B: Expand LangGraph
1. Implement node functions (plan, execute, reflect)
2. Add conditional routing logic
3. Implement state management
4. Test with Notion tools

### Phase 3C: Working Memory
1. Implement Redis-backed working memory
2. Store step results and context
3. Add context retrieval for LLM prompts

### Phase 3D: End-to-End Testing
1. Create example workflows
2. Test all autonomy levels
3. Validate error handling
4. Performance optimization

---

## Questions for Discussion

1. **LLM Provider**: Which LLM should we use?
   - Anthropic Claude (Sonnet 3.5, Opus)
   - OpenAI (GPT-4, GPT-4-turbo)
   - Other (Gemini, Llama, etc.)

2. **Workflow Priorities**: Which workflow should we build first?
   - Weekly meeting summary
   - Knowledge discovery and indexing
   - Proactive monitoring
   - Content synthesis

3. **Autonomy Default**: What default autonomy level?
   - L1 (Draft) - Safe, requires approval
   - L2 (ExecuteNotify) - Faster, autonomous

4. **Working Memory**: How long to keep context?
   - 1 hour (short-lived)
   - 24 hours (day-long workflows)
   - 7 days (week-long projects)

---

**Ready to discuss these design decisions?** 🚀
