"""LLM Router - Intelligently routes tasks to ChatGPT-5 or Claude.

Routing Strategy:
- ChatGPT-5: User responses, summaries, conversational tasks
- Claude: Planning, technical reasoning, reflection, analysis
"""

import re
from enum import Enum
from typing import Any

from .client import LLMClient
from .openai_client import OpenAIClient
from .anthropic_client import AnthropicClient


class TaskType(Enum):
    """Types of tasks for LLM routing."""

    # ChatGPT-5 tasks
    USER_RESPONSE = "user_response"  # Conversational responses
    SUMMARIZATION = "summarization"  # Content summarization
    FORMATTING = "formatting"  # Output formatting
    TRANSLATION = "translation"  # Language translation

    # Claude tasks
    PLANNING = "planning"  # Execution planning
    TECHNICAL_ANALYSIS = "technical_analysis"  # Code/technical analysis
    REFLECTION = "reflection"  # Progress evaluation
    DECISION_MAKING = "decision_making"  # Complex decisions


class LLMRouter:
    """Routes tasks to appropriate LLM based on task type."""

    # Keywords that indicate Claude should handle the task
    CLAUDE_KEYWORDS = [
        "plan",
        "analyze",
        "evaluate",
        "reflect",
        "reason",
        "decide",
        "technical",
        "code",
        "architecture",
        "strategy",
        "execution",
        "steps",
        "workflow",
    ]

    # Keywords that indicate ChatGPT should handle the task
    CHATGPT_KEYWORDS = [
        "summarize",
        "explain",
        "describe",
        "format",
        "translate",
        "user",
        "friendly",
        "conversational",
        "readable",
    ]

    def __init__(
        self,
        openai_client: OpenAIClient | None = None,
        anthropic_client: AnthropicClient | None = None,
    ):
        """Initialize router with LLM clients.

        Args:
            openai_client: ChatGPT-5 client (created if not provided)
            anthropic_client: Claude client (created if not provided)
        """
        self.chatgpt = openai_client or OpenAIClient()
        self.claude = anthropic_client or AnthropicClient()

    def route(self, task_type: TaskType) -> LLMClient:
        """Route task to appropriate LLM based on task type.

        Args:
            task_type: Type of task to perform

        Returns:
            Appropriate LLM client
        """
        chatgpt_tasks = {
            TaskType.USER_RESPONSE,
            TaskType.SUMMARIZATION,
            TaskType.FORMATTING,
            TaskType.TRANSLATION,
        }

        if task_type in chatgpt_tasks:
            return self.chatgpt
        else:
            return self.claude

    def route_from_prompt(self, prompt: str) -> LLMClient:
        """Route based on prompt content analysis.

        Args:
            prompt: Prompt text to analyze

        Returns:
            Appropriate LLM client
        """
        prompt_lower = prompt.lower()

        # Count keyword matches
        claude_score = sum(
            1 for keyword in self.CLAUDE_KEYWORDS if keyword in prompt_lower
        )
        chatgpt_score = sum(
            1 for keyword in self.CHATGPT_KEYWORDS if keyword in prompt_lower
        )

        # Claude handles technical/planning tasks
        if claude_score > chatgpt_score:
            return self.claude
        else:
            return self.chatgpt

    async def generate(
        self,
        prompt: str,
        task_type: TaskType | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> tuple[str, str]:
        """Generate response using routed LLM.

        Args:
            prompt: User prompt
            task_type: Optional explicit task type (otherwise inferred)
            system_prompt: System instructions
            temperature: Sampling temperature
            max_tokens: Max tokens
            **kwargs: Additional parameters

        Returns:
            Tuple of (response text, model_name used)
        """
        # Route to appropriate model
        if task_type:
            client = self.route(task_type)
        else:
            client = self.route_from_prompt(prompt)

        # Generate response
        response = await client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        return response, client.model_name

    async def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        task_type: TaskType | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], str]:
        """Generate structured JSON using routed LLM.

        Args:
            prompt: User prompt
            schema: JSON schema
            task_type: Optional explicit task type
            system_prompt: System instructions
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            Tuple of (parsed JSON, model_name used)
        """
        # Route to appropriate model
        if task_type:
            client = self.route(task_type)
        else:
            client = self.route_from_prompt(prompt)

        # Generate JSON
        result = await client.generate_json(
            prompt=prompt,
            schema=schema,
            system_prompt=system_prompt,
            temperature=temperature,
            **kwargs,
        )

        return result, client.model_name

    def get_client(self, task_type: TaskType) -> LLMClient:
        """Get client for specific task type.

        Args:
            task_type: Type of task

        Returns:
            LLM client
        """
        return self.route(task_type)
