"""Chad-Core LLM Integration.

Dual-LLM architecture:
- ChatGPT-5: User interactions, summarization, conversational responses
- Claude: Technical planning, execution reasoning, reflection, analysis

The LLM Router intelligently selects which model to use based on task type.
"""

from .client import LLMClient
from .openai_client import OpenAIClient
from .anthropic_client import AnthropicClient
from .router import LLMRouter, TaskType

__all__ = [
    "LLMClient",
    "OpenAIClient",
    "AnthropicClient",
    "LLMRouter",
    "TaskType",
]
