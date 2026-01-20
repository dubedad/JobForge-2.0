"""OpenAI client wrapper for structured LLM outputs.

Provides a thin wrapper around the OpenAI API with support for
Structured Outputs to ensure type-safe responses for imputation.
"""

import os
from typing import TypeVar

from pydantic import BaseModel

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore

# Model that supports Structured Outputs
LLM_IMPUTATION_MODEL = "gpt-4o-2024-08-06"

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """OpenAI client wrapper with Structured Outputs support.

    Wraps the OpenAI API to provide type-safe parsing of LLM responses
    into Pydantic models using Structured Outputs.

    Attributes:
        client: The underlying OpenAI client instance.
        model: The model to use for completions.

    Example:
        >>> client = LLMClient()
        >>> response = client.parse(
        ...     messages=[{"role": "user", "content": "Hello"}],
        ...     response_format=MyResponseModel,
        ... )
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = LLM_IMPUTATION_MODEL,
    ):
        """Initialize the LLM client.

        Args:
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
            model: Model to use for completions. Defaults to gpt-4o-2024-08-06.

        Raises:
            ImportError: If openai package is not installed.
        """
        if OpenAI is None:
            raise ImportError(
                "openai package is required for LLM imputation. "
                "Install with: pip install 'openai>=1.52.0'"
            )

        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=resolved_key) if resolved_key else None
        self.model = model
        self._api_key = resolved_key

    def parse(
        self,
        messages: list[dict],
        response_format: type[T],
        max_tokens: int = 1000,
    ) -> T:
        """Parse LLM response into a Pydantic model using Structured Outputs.

        Uses OpenAI's beta.chat.completions.parse API to ensure the response
        conforms to the provided Pydantic model schema.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            response_format: Pydantic model class to parse response into.
            max_tokens: Maximum tokens in the response.

        Returns:
            Instance of response_format populated with LLM response.

        Raises:
            ValueError: If no API key is configured.
            openai.APIError: If the API call fails.
        """
        if self.client is None:
            raise ValueError(
                "No OpenAI API key configured. "
                "Set OPENAI_API_KEY environment variable or pass api_key to constructor."
            )

        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=messages,
            response_format=response_format,
            max_tokens=max_tokens,
        )
        return completion.choices[0].message.parsed

    def is_available(self) -> bool:
        """Check if the client is configured with an API key.

        Returns:
            True if an API key is configured, False otherwise.
        """
        return self._api_key is not None and len(self._api_key) > 0
