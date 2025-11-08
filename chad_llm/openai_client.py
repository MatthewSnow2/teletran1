"""OpenAI client for ChatGPT-5 integration.

Used for:
- User-facing conversational responses
- Content summarization
- Natural language generation
- Final output formatting
"""

import json
import os
from typing import Any

from openai import AsyncOpenAI
from openai import APIError, AuthenticationError, RateLimitError

from .client import (
    LLMClient,
    LLMError,
    LLMAuthError,
    LLMRateLimitError,
    LLMValidationError,
)


class OpenAIClient(LLMClient):
    """ChatGPT-5 client for conversational and summarization tasks."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-5-2025-08-07",  # GPT-5 (August 2025)
        organization: str | None = None,
    ):
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use (default: gpt-5-2025-08-07)
            organization: Optional organization ID
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise LLMAuthError("OPENAI_API_KEY not found in environment")

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            organization=organization,
        )
        self._model = model

    @property
    def model_name(self) -> str:
        """Return model identifier."""
        return self._model

    @property
    def max_context_tokens(self) -> int:
        """Return max context window."""
        if "gpt-5" in self._model:
            return 200000  # GPT-5 context window
        elif "gpt-4o" in self._model:
            return 128000
        elif "gpt-4-turbo" in self._model:
            return 128000
        elif "gpt-4" in self._model:
            return 8192
        else:
            return 4096  # Conservative default

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> str:
        """Generate text completion using ChatGPT-5.

        Args:
            prompt: User prompt
            system_prompt: System instructions
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional OpenAI parameters

        Returns:
            Generated text

        Raises:
            LLMAuthError: Invalid API key
            LLMRateLimitError: Rate limit exceeded
            LLMError: Other API errors
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        try:
            # GPT-5 has specific parameter constraints
            api_params = {
                "model": self._model,
                "messages": messages,
                **kwargs,
            }

            # Handle model-specific parameters
            if "gpt-5" in self._model:
                # GPT-5: use max_completion_tokens, temperature must be 1.0 (default)
                api_params["max_completion_tokens"] = max_tokens
                # Don't set temperature for GPT-5 (only supports default 1.0)
            else:
                # GPT-4 and earlier: use max_tokens, custom temperature supported
                api_params["max_tokens"] = max_tokens
                api_params["temperature"] = temperature

            response = await self.client.chat.completions.create(**api_params)

            return response.choices[0].message.content or ""

        except AuthenticationError as e:
            raise LLMAuthError(f"OpenAI authentication failed: {e}")
        except RateLimitError as e:
            raise LLMRateLimitError(f"OpenAI rate limit exceeded: {e}")
        except APIError as e:
            raise LLMError(f"OpenAI API error: {e}")

    async def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate structured JSON using function calling.

        Args:
            prompt: User prompt
            schema: JSON schema for output structure
            system_prompt: System instructions
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            Parsed JSON object

        Raises:
            LLMValidationError: If output doesn't match schema
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        # Convert JSON schema to OpenAI function format
        function_def = {
            "name": "structured_output",
            "description": "Return structured data matching the schema",
            "parameters": schema,
        }

        try:
            # GPT-5 may not support legacy function calling, use response_format instead
            if "gpt-5" in self._model:
                # Use JSON mode for GPT-5 (temperature must be 1.0, default)
                response = await self.client.chat.completions.create(
                    model=self._model,
                    messages=messages + [{
                        "role": "user",
                        "content": f"Return JSON matching this schema: {json.dumps(schema)}"
                    }],
                    response_format={"type": "json_object"},
                    # Note: temperature omitted for GPT-5 (only supports 1.0)
                    **kwargs,
                )
                # Parse JSON from content
                content = response.choices[0].message.content
                if content:
                    return json.loads(content)
                else:
                    raise LLMValidationError("No content in response")
            else:
                # Use legacy function calling for GPT-4 (supports custom temperature)
                response = await self.client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=temperature,
                    functions=[function_def],
                    function_call={"name": "structured_output"},
                    **kwargs,
                )

                # Extract function call arguments
                function_call = response.choices[0].message.function_call
                if not function_call:
                    raise LLMValidationError("Model did not return function call")

                result = json.loads(function_call.arguments)
                return result

        except json.JSONDecodeError as e:
            raise LLMValidationError(f"Failed to parse JSON: {e}")
        except AuthenticationError as e:
            raise LLMAuthError(f"OpenAI authentication failed: {e}")
        except RateLimitError as e:
            raise LLMRateLimitError(f"OpenAI rate limit exceeded: {e}")
        except APIError as e:
            raise LLMError(f"OpenAI API error: {e}")

    async def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken.

        Note: This is an approximation. For exact counts, use tiktoken directly.

        Args:
            text: Text to count

        Returns:
            Approximate token count (chars / 4)
        """
        # Simple approximation: ~4 chars per token
        # For production, use: tiktoken.encoding_for_model(self._model)
        return len(text) // 4
