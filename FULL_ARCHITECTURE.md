# Chad-Core Full Architecture Design

**Version**: 2.0
**Date**: 2025-11-03
**Status**: Design Phase
**Autonomy**: L2 (ExecuteNotify - Autonomous with Notification)

---

## Executive Summary

Chad-Core is a dual-LLM autonomous knowledge agent that:
- Uses **ChatGPT-5** for conversational user interactions
- Uses **Claude** for technical planning, reasoning, and code generation
- Manages knowledge in **Notion** as the primary knowledge base
- Operates at **L2 autonomy** - executes autonomously, notifies on completion
- Focuses on **knowledge organization** as the primary workflow

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER LAYER                               │
│  - n8n workflows                                                 │
│  - ChatGPT-5 conversational interface                           │
│  - Direct API calls                                              │
└────────────────────────┬────────────────────────────────────────┘
                         │ POST /act (JWT + HMAC)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CHAD-CORE API (FastAPI)                       │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              REQUEST HANDLER                             │   │
│  │  1. Auth validation (JWT + HMAC)                        │   │
│  │  2. Policy guard (check actor permissions)              │   │
│  │  3. Autonomy level determination (L0-L3)                │   │
│  │  4. Idempotency check (Redis)                           │   │
│  │  5. Rate limiting                                        │   │
│  └──────────────────────┬──────────────────────────────────┘   │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           LANGGRAPH EXECUTION ENGINE                     │   │
│  │                                                          │   │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐         │   │
│  │  │  PLAN    │───▶│ EXECUTE  │───▶│ REFLECT  │         │   │
│  │  │ (Claude) │    │  (Tools) │    │ (Claude) │         │   │
│  │  └──────────┘    └──────────┘    └──────────┘         │   │
│  │       │               │                │                │   │
│  │       └───────────────┴────────────────┘                │   │
│  │                       │                                  │   │
│  │                       ▼                                  │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │          WORKING MEMORY (Redis)                  │   │   │
│  │  │  - Execution state                               │   │   │
│  │  │  - Step results                                  │   │   │
│  │  │  - LLM context                                   │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   LLM LAYER  │  │  TOOL LAYER  │  │ MEMORY LAYER │
│              │  │              │  │              │
│ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │
│ │ChatGPT-5 │ │  │ │  Notion  │ │  │ │ Postgres │ │
│ │(OpenAI)  │ │  │ │  Search  │ │  │ │(Supabase)│ │
│ └──────────┘ │  │ │   Read   │ │  │ └──────────┘ │
│              │  │ │  Create  │ │  │              │
│ ┌──────────┐ │  │ │  Query   │ │  │ ┌──────────┐ │
│ │ Claude   │ │  │ └──────────┘ │  │ │  Redis   │ │
│ │(Anthropic│ │  │              │  │ │          │ │
│ └──────────┘ │  │ ┌──────────┐ │  │ └──────────┘ │
│              │  │ │  Future  │ │  │              │
│ ┌──────────┐ │  │ │  GitHub  │ │  │ ┌──────────┐ │
│ │LLM Router│ │  │ │  Google  │ │  │ │Supabase  │ │
│ │          │ │  │ │  Slack   │ │  │ │ Storage  │ │
│ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## Dual-LLM Architecture

### LLM Router Pattern

Chad-Core uses an intelligent **LLM Router** to decide which LLM to use for each task:

```python
class LLMRouter:
    """Route LLM requests to ChatGPT-5 or Claude based on task type."""

    def route(self, task_type: str, context: dict) -> LLM:
        """
        Routing Logic:

        ChatGPT-5 (Conversational):
        - User-facing responses
        - Q&A interactions
        - Summarization for end-users
        - Natural language generation

        Claude (Technical):
        - Execution planning
        - Technical reasoning
        - Code generation
        - Complex analysis
        - Self-reflection
        """

        if task_type in ["plan", "reflect", "analyze", "code"]:
            return self.claude
        elif task_type in ["respond", "summarize", "chat", "explain"]:
            return self.chatgpt
        else:
            # Default to Claude for safety (better reasoning)
            return self.claude
```

### LLM Responsibilities

#### **ChatGPT-5 (OpenAI)**
```python
# Use for:
1. User-facing responses
   - "Here's what I found in your Notion workspace..."
   - "I've organized your pages into 5 categories..."

2. Content summarization
   - Summarize meeting notes for humans
   - Create readable reports

3. Conversational interactions
   - Answer user questions
   - Explain what Chad is doing

4. Natural language generation
   - Create page titles
   - Write descriptions
```

#### **Claude (Anthropic)**
```python
# Use for:
1. Execution planning
   - Generate step-by-step plans
   - Decide which tools to use

2. Technical reasoning
   - Analyze code
   - Debug issues
   - Self-correction

3. Reflection & self-evaluation
   - "Did the plan work?"
   - "Should I adjust my approach?"

4. Complex categorization
   - Group pages by topic
   - Extract technical concepts
```

---

## Knowledge Organization Workflow (Primary Use Case)

### Workflow: Autonomous Knowledge Organizer

**Goal**: Automatically organize and index Notion pages by topic

**Trigger**:
- Daily cron job (n8n)
- Manual: POST /act with goal "Organize my knowledge base"
- Continuous: Watch for new pages

**Execution Flow**:

```
┌──────────────────────────────────────────────────────────┐
│ STEP 1: DISCOVERY (Notion Search)                        │
│ Tool: notion.search                                       │
│ Input: {"query": "", "max_results": 100}                 │
│ Output: List of all accessible pages                     │
└────────────────────┬─────────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────────────────┐
│ STEP 2: CONTENT EXTRACTION (Notion Read)                 │
│ Tool: notion.pages.read                                   │
│ Input: {"page_id": "<each_page>"}                        │
│ Output: Markdown content of each page                    │
│ Working Memory: Store all page contents                  │
└────────────────────┬─────────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────────────────┐
│ STEP 3: CATEGORIZATION (Claude Analysis)                 │
│ LLM: Claude                                               │
│ Task: "Analyze these pages and categorize by topic"      │
│ Input: All page titles + first 500 chars of content     │
│ Output: JSON category mapping                            │
│ Example:                                                  │
│ {                                                         │
│   "Programming": ["Python Guide", "API Docs"],          │
│   "Projects": ["Chad-Core", "Portfolio Site"],          │
│   "Notes": ["Meeting Notes", "Ideas"]                   │
│ }                                                         │
└────────────────────┬─────────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────────────────┐
│ STEP 4: INDEX CREATION (Notion Create)                   │
│ Tool: notion.pages.create                                 │
│ For each category:                                        │
│   1. Create index page with category name                │
│   2. Add links to all pages in that category            │
│   3. Add summary generated by ChatGPT-5                  │
│ Output: List of created index pages                      │
└────────────────────┬─────────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────────────────┐
│ STEP 5: MASTER INDEX (Notion Create)                     │
│ Tool: notion.pages.create                                 │
│ Create "📚 Knowledge Base Index" page                    │
│ Contents:                                                 │
│   - Links to all category index pages                   │
│   - Statistics (total pages, categories)                │
│   - Last updated timestamp                               │
│   - Quick search guide                                   │
└────────────────────┬─────────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────────────────┐
│ STEP 6: USER NOTIFICATION (L2 Autonomy)                  │
│ Method: Webhook to n8n OR direct message                 │
│ Message: "✅ Organized 47 pages into 5 categories.      │
│          View index: https://notion.so/knowledge-base"   │
└──────────────────────────────────────────────────────────┘
```

### Detailed Step Breakdown

#### Step 1-2: Discovery & Extraction
```python
# Execute in parallel for performance
async def discover_and_extract(ctx):
    # Step 1: Search
    search_result = await notion_search_tool.execute(
        ctx=ctx,
        input_data={"query": "", "max_results": 100}
    )

    # Step 2: Read all pages (parallel)
    pages_content = await asyncio.gather(*[
        notion_read_page_tool.execute(
            ctx=ctx,
            input_data={"page_id": page["id"]}
        )
        for page in search_result["results"]
        if page["type"] == "page"  # Skip databases
    ])

    return pages_content
```

#### Step 3: Categorization with Claude
```python
async def categorize_pages(pages_content):
    # Build Claude prompt
    prompt = f"""
You are analyzing a Notion workspace to organize pages by topic.

Pages to categorize:
{format_pages_for_llm(pages_content)}

Task:
1. Identify major themes/topics across these pages
2. Group pages into 3-7 meaningful categories
3. Suggest a clear category name for each group
4. Include a brief description of what each category contains

Output as JSON:
{{
  "categories": [
    {{
      "name": "Category Name",
      "description": "What this category contains",
      "pages": ["page_id_1", "page_id_2"],
      "icon_emoji": "📁"
    }}
  ],
  "uncategorized": ["page_id_x"],
  "reasoning": "Why you chose these categories"
}}
"""

    result = await claude.generate_json(
        prompt=prompt,
        max_tokens=4000
    )

    return result
```

#### Step 4-5: Index Creation
```python
async def create_indexes(categories, ctx):
    index_pages = []

    # Create category index pages
    for category in categories["categories"]:
        # Build page content with ChatGPT-5
        summary = await chatgpt.generate(f"""
Summarize this category for users:
Category: {category["name"]}
Description: {category["description"]}
Pages: {len(category["pages"])} pages

Write a friendly 2-3 sentence overview.
""")

        # Build markdown content
        content = f"""
# {category["icon_emoji"]} {category["name"]}

{summary}

## Pages in this category

{build_page_links(category["pages"])}

---
*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
*Auto-generated by Chad-Core Knowledge Organizer*
"""

        # Create page
        result = await notion_create_page_tool.execute(
            ctx=ctx,
            input_data={
                "parent_id": "workspace",
                "title": f"{category['icon_emoji']} {category['name']}",
                "content_markdown": content,
                "icon_emoji": category["icon_emoji"]
            }
        )

        index_pages.append(result)

    # Create master index
    master_index = await create_master_index(index_pages, ctx)

    return master_index
```

#### Step 6: L2 Notification
```python
async def notify_user(result, ctx):
    """Send notification via webhook or message."""

    # Build user-friendly message with ChatGPT-5
    message = await chatgpt.generate(f"""
Generate a friendly notification message for this result:

Action: Organized Notion workspace
Categories created: {len(result["categories"])}
Total pages organized: {result["total_pages"]}
Master index URL: {result["master_index_url"]}

Write a concise, upbeat notification (2-3 sentences).
""")

    # Send via webhook (n8n)
    await send_webhook(
        url=ctx["webhook_url"],
        data={
            "type": "knowledge_organization_complete",
            "message": message,
            "details": result
        }
    )
```

---

## LangGraph Implementation

### State Schema

```python
from typing import TypedDict, Literal

class AgentState(TypedDict):
    """State passed between LangGraph nodes."""

    # Execution metadata
    run_id: str
    actor: str
    goal: str
    autonomy_level: Literal["L0", "L1", "L2", "L3"]

    # Planning
    plan: list[dict]  # Generated by Claude
    current_step: int
    max_steps: int

    # Execution
    executed_steps: list[dict]
    working_memory: dict  # Results from previous steps

    # LLM context
    messages: list  # Conversation history
    llm_calls: int  # Track usage

    # Results
    final_result: dict | None
    status: Literal["pending", "running", "completed", "failed"]
    error: str | None

    # Artifacts
    artifacts: list[dict]  # Created pages, files, etc.
```

### Graph Definition

```python
from langgraph.graph import StateGraph, END

def create_knowledge_organization_graph():
    """Create LangGraph for knowledge organization workflow."""

    graph = StateGraph(AgentState)

    # Nodes
    graph.add_node("initialize", initialize_node)
    graph.add_node("plan", plan_node)  # Claude plans execution
    graph.add_node("execute_tool", execute_tool_node)  # Run Notion tools
    graph.add_node("reflect", reflect_node)  # Claude evaluates progress
    graph.add_node("finalize", finalize_node)  # Wrap up, notify user

    # Entry point
    graph.set_entry_point("initialize")

    # Edges
    graph.add_edge("initialize", "plan")
    graph.add_edge("plan", "execute_tool")

    # Conditional routing after execution
    graph.add_conditional_edges(
        "execute_tool",
        decide_after_execution,
        {
            "continue": "reflect",
            "done": "finalize",
            "error": "finalize"
        }
    )

    # Conditional routing after reflection
    graph.add_conditional_edges(
        "reflect",
        decide_after_reflection,
        {
            "continue": "execute_tool",  # Next step
            "replan": "plan",  # Adjust plan
            "done": "finalize"  # Goal achieved
        }
    )

    # End
    graph.add_edge("finalize", END)

    return graph.compile()
```

### Node Implementations

#### Initialize Node
```python
async def initialize_node(state: AgentState) -> AgentState:
    """Initialize execution context."""

    state["status"] = "running"
    state["current_step"] = 0
    state["executed_steps"] = []
    state["working_memory"] = {}
    state["artifacts"] = []
    state["llm_calls"] = 0
    state["messages"] = []

    # Store in Redis for persistence
    await redis.set(
        f"run:{state['run_id']}:state",
        json.dumps(state),
        ex=3600  # 1 hour TTL
    )

    return state
```

#### Plan Node (Claude)
```python
async def plan_node(state: AgentState) -> AgentState:
    """Generate execution plan using Claude."""

    # Check if replanning or first plan
    is_replan = len(state["executed_steps"]) > 0

    if is_replan:
        prompt = f"""
You are Chad, an autonomous knowledge agent.

Goal: {state["goal"]}

Previous execution:
{json.dumps(state["executed_steps"], indent=2)}

The previous plan didn't fully achieve the goal. Create a revised plan.
"""
    else:
        prompt = f"""
You are Chad, an autonomous knowledge agent with access to Notion.

Goal: {state["goal"]}

Available Tools:
1. notion.search(query, max_results) - Search workspace for pages
2. notion.pages.read(page_id) - Read full page content as markdown
3. notion.pages.create(parent_id, title, content_markdown, icon_emoji) - Create new pages
4. notion.databases.query(database_id, filter_conditions) - Query databases

Create a step-by-step execution plan. For each step:
- Specify which tool to use
- Define exact inputs (use {{step_N_result.field}} for data from previous steps)
- Explain what the step accomplishes

Output as JSON:
{{
  "steps": [
    {{
      "tool": "notion.search",
      "input": {{"query": "", "max_results": 100}},
      "purpose": "Discover all pages in workspace"
    }},
    ...
  ],
  "expected_outcome": "What success looks like",
  "estimated_duration": "How long this will take"
}}
"""

    # Call Claude
    response = await claude.generate_json(
        prompt=prompt,
        max_tokens=4000,
        temperature=0.3  # Lower temp for planning
    )

    state["plan"] = response["steps"]
    state["llm_calls"] += 1
    state["messages"].append({
        "role": "assistant",
        "content": f"Plan created with {len(response['steps'])} steps"
    })

    return state
```

#### Execute Tool Node
```python
async def execute_tool_node(state: AgentState) -> AgentState:
    """Execute current step's tool."""

    step_index = state["current_step"]
    step = state["plan"][step_index]

    # Resolve inputs from working memory
    resolved_input = resolve_template_inputs(
        step["input"],
        state["working_memory"]
    )

    # Get tool from registry
    tool = tool_registry.get(step["tool"])

    try:
        # Execute tool
        result = await tool.execute(
            ctx={
                "actor": state["actor"],
                "run_id": state["run_id"]
            },
            input_data=resolved_input
        )

        # Store result
        state["executed_steps"].append({
            "step": step_index,
            "tool": step["tool"],
            "input": resolved_input,
            "output": result,
            "status": "success",
            "timestamp": datetime.now().isoformat()
        })

        # Update working memory
        state["working_memory"][f"step_{step_index}_result"] = result

        # Track artifacts (created pages, etc.)
        if step["tool"] == "notion.pages.create":
            state["artifacts"].append({
                "type": "notion_page",
                "url": result["url"],
                "title": result["title"],
                "page_id": result["page_id"]
            })

        state["current_step"] += 1

    except Exception as e:
        state["executed_steps"].append({
            "step": step_index,
            "tool": step["tool"],
            "input": resolved_input,
            "error": str(e),
            "status": "failed",
            "timestamp": datetime.now().isoformat()
        })
        state["error"] = str(e)
        state["status"] = "failed"

    return state
```

#### Reflect Node (Claude)
```python
async def reflect_node(state: AgentState) -> AgentState:
    """Reflect on progress using Claude."""

    prompt = f"""
You are Chad, reflecting on execution progress.

Goal: {state["goal"]}

Plan:
{json.dumps(state["plan"], indent=2)}

Executed Steps:
{json.dumps(state["executed_steps"], indent=2)}

Working Memory:
{json.dumps(state["working_memory"], indent=2)}

Analyze:
1. Have we achieved the goal?
2. Are there any errors or issues?
3. Should we continue with the plan, replan, or finish?

Output as JSON:
{{
  "goal_achieved": true/false,
  "next_action": "continue" | "replan" | "done",
  "reasoning": "Detailed explanation of your analysis",
  "success_metrics": {{
    "pages_organized": 0,
    "categories_created": 0,
    "errors": 0
  }}
}}
"""

    response = await claude.generate_json(
        prompt=prompt,
        max_tokens=2000
    )

    state["llm_calls"] += 1
    state["messages"].append({
        "role": "assistant",
        "content": response["reasoning"]
    })

    # Store reflection in working memory
    state["working_memory"]["reflection"] = response

    return state
```

#### Finalize Node
```python
async def finalize_node(state: AgentState) -> AgentState:
    """Finalize execution and prepare user notification."""

    # Determine final status
    if state.get("error"):
        state["status"] = "failed"
    else:
        state["status"] = "completed"

    # Build final result
    state["final_result"] = {
        "status": state["status"],
        "goal": state["goal"],
        "steps_executed": len(state["executed_steps"]),
        "llm_calls": state["llm_calls"],
        "artifacts": state["artifacts"],
        "duration_seconds": calculate_duration(state),
        "error": state.get("error")
    }

    # L2 Autonomy: Generate notification with ChatGPT-5
    if state["autonomy_level"] == "L2":
        notification = await chatgpt.generate(f"""
Generate a friendly notification message for the user.

Task completed: {state["goal"]}
Status: {state["status"]}
Results: {json.dumps(state["final_result"], indent=2)}

Write a concise, positive message (2-3 sentences).
Include relevant links or key metrics.
""")

        state["final_result"]["notification"] = notification

        # Send notification (via webhook, email, etc.)
        await notify_user(state)

    # Persist final state
    await redis.set(
        f"run:{state['run_id']}:final",
        json.dumps(state["final_result"]),
        ex=86400  # 24 hours
    )

    return state
```

### Routing Functions

```python
def decide_after_execution(state: AgentState) -> str:
    """Decide next step after tool execution."""

    # Check for errors
    last_step = state["executed_steps"][-1]
    if last_step["status"] == "failed":
        return "error"

    # Check if all steps completed
    if state["current_step"] >= len(state["plan"]):
        return "done"

    # Continue to reflection
    return "continue"

def decide_after_reflection(state: AgentState) -> str:
    """Decide next step after reflection."""

    reflection = state["working_memory"].get("reflection", {})

    if reflection.get("goal_achieved"):
        return "done"
    elif reflection.get("next_action") == "replan":
        return "replan"
    else:
        return "continue"
```

---

## Working Memory & State Management

### Redis Schema

```
# Execution state
run:{run_id}:state → AgentState (JSON)
run:{run_id}:final → FinalResult (JSON)

# Step results
run:{run_id}:step:{step_number} → StepResult (JSON)

# LLM context
run:{run_id}:llm:calls → List of LLM calls
run:{run_id}:llm:tokens → Token usage tracking

# Idempotency
idempotency:{key} → run_id (24h TTL)

# Rate limiting
rate_limit:{actor}:{minute} → count (60s TTL)
```

### State Persistence

```python
class WorkingMemoryStore:
    """Redis-backed working memory."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def save_state(self, run_id: str, state: AgentState):
        """Save full agent state."""
        await self.redis.set(
            f"run:{run_id}:state",
            json.dumps(state),
            ex=3600  # 1 hour
        )

    async def get_state(self, run_id: str) -> AgentState | None:
        """Retrieve agent state."""
        data = await self.redis.get(f"run:{run_id}:state")
        return json.loads(data) if data else None

    async def save_step_result(self, run_id: str, step: int, result: dict):
        """Save individual step result."""
        await self.redis.set(
            f"run:{run_id}:step:{step}",
            json.dumps(result),
            ex=3600
        )

    async def track_llm_call(self, run_id: str, model: str, tokens: int):
        """Track LLM usage."""
        await self.redis.lpush(
            f"run:{run_id}:llm:calls",
            json.dumps({
                "model": model,
                "tokens": tokens,
                "timestamp": datetime.now().isoformat()
            })
        )
        await self.redis.expire(f"run:{run_id}:llm:calls", 3600)
```

---

## API Integration

### /act Endpoint (Full Implementation)

```python
# apps/core_api/routers/act.py

@router.post("/act")
async def act_endpoint(
    request: ActRequest,
    auth: dict = Depends(validate_jwt),
    hmac_valid: None = Depends(validate_hmac)
):
    """Execute agent workflow with LangGraph."""

    # 1. Generate run ID
    run_id = str(uuid.uuid4())

    # 2. Check idempotency
    if request.idempotency_key:
        existing_run = await check_idempotency(request.idempotency_key)
        if existing_run:
            return JSONResponse(
                status_code=409,
                content={"error": "duplicate_request", "run_id": existing_run}
            )

    # 3. Determine autonomy level
    autonomy = determine_autonomy_level(
        actor=request.actor,
        goal=request.goal,
        context=request.context
    )

    # 4. Initialize state
    initial_state = AgentState(
        run_id=run_id,
        actor=request.actor,
        goal=request.goal,
        autonomy_level=autonomy,
        plan=[],
        current_step=0,
        max_steps=request.max_steps or 10,
        executed_steps=[],
        working_memory={},
        messages=[],
        llm_calls=0,
        final_result=None,
        status="pending",
        error=None,
        artifacts=[]
    )

    # 5. Create and run graph
    graph = create_knowledge_organization_graph()

    # 6. Execute async (return 202 if >30s expected)
    if request.timeout_seconds and request.timeout_seconds < 30:
        # Synchronous execution
        result = await graph.ainvoke(initial_state)
        return ActResponse(
            run_id=run_id,
            trace_id=generate_trace_id(),
            status=result["status"],
            autonomy_level=autonomy,
            plan=result["plan"],
            results=result["executed_steps"],
            artifacts=result["artifacts"],
            final_result=result["final_result"]
        )
    else:
        # Async execution (queue worker)
        await queue_execution(run_id, initial_state)
        return JSONResponse(
            status_code=202,
            content={
                "run_id": run_id,
                "status": "pending",
                "poll_url": f"/runs/{run_id}",
                "autonomy_level": autonomy
            }
        )
```

---

## Implementation Roadmap

### Phase 3A: LLM Integration (2-3 hours)

**Files to Create:**
```
chad_llm/
├── __init__.py
├── client.py          # Base LLM client interface
├── openai_client.py   # ChatGPT-5 client
├── anthropic_client.py # Claude client
└── router.py          # LLM routing logic
```

**Tasks:**
1. Install SDKs: `openai`, `anthropic`
2. Implement client wrappers with retry logic
3. Add structured output support (JSON mode)
4. Implement LLM router
5. Add token tracking

### Phase 3B: LangGraph Nodes (3-4 hours)

**Files to Modify:**
```
chad_agents/graphs/graph_langgraph.py
```

**Tasks:**
1. Define `AgentState` schema
2. Implement 5 nodes (initialize, plan, execute, reflect, finalize)
3. Add routing functions
4. Create graph compiler
5. Add error handling

### Phase 3C: Working Memory (1-2 hours)

**Files to Create:**
```
chad_memory/working_memory.py
```

**Tasks:**
1. Implement Redis-backed state store
2. Add state persistence methods
3. Add LLM call tracking
4. Implement context retrieval

### Phase 3D: API Integration (1-2 hours)

**Files to Modify:**
```
apps/core_api/routers/act.py
apps/core_api/deps.py
```

**Tasks:**
1. Connect /act endpoint to LangGraph
2. Add async execution queue
3. Implement idempotency checking
4. Add L2 notification logic

### Phase 3E: Testing (2-3 hours)

**Files to Create:**
```
tests/test_knowledge_organization.py
tests/test_llm_integration.py
tests/test_langgraph.py
```

**Tasks:**
1. Create end-to-end test
2. Test with real Notion workspace
3. Validate LLM calls
4. Test error handling
5. Performance testing

---

## Total Implementation Estimate

**Total Time**: 9-14 hours
- Phase 3A: 2-3 hours
- Phase 3B: 3-4 hours
- Phase 3C: 1-2 hours
- Phase 3D: 1-2 hours
- Phase 3E: 2-3 hours

---

## Next Steps

1. **Get API Keys**:
   - OpenAI API key (for ChatGPT-5/GPT-4)
   - Anthropic API key (for Claude)

2. **Start with Phase 3A** (LLM Integration):
   - Simplest starting point
   - Can test immediately
   - Builds foundation for rest

3. **Test Incrementally**:
   - After each phase, run tests
   - Validate with real Notion workspace

---

**Ready to start implementation?** 🚀
