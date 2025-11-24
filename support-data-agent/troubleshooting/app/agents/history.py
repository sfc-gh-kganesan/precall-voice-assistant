"""History processors for managing conversation memory.

Based on Pydantic AI's history processor pattern:
https://ai.pydantic.dev/messages/#processing-message-history
"""

import logging
from typing import Callable, List

from pydantic_ai import ModelMessage

logger = logging.getLogger(__name__)


def keep_last_n_messages(
    n: int = 10,
) -> Callable[[List[ModelMessage]], List[ModelMessage]]:
    """Keep only the last N messages to limit memory growth.

    Args:
        n: Number of recent messages to keep (default: 10)

    Returns:
        A history processor function that limits message count

    Example:
        >>> agent = Agent(
        ...     'openai:gpt-4',
        ...     history_processors=[keep_last_n_messages(10)]
        ... )
    """

    def processor(messages: List[ModelMessage]) -> List[ModelMessage]:
        if len(messages) > n:
            logger.debug(
                f"Trimming conversation history from {len(messages)} to {n} messages"
            )
            return messages[-n:]
        return messages

    return processor


def keep_last_n_tokens(
    max_tokens: int = 4000,
) -> Callable[[List[ModelMessage]], List[ModelMessage]]:
    """Keep messages that fit within a token budget (approximate).

    Note: This is an approximation based on character count.
    For accurate token counting, integrate with tiktoken or similar.

    Args:
        max_tokens: Maximum approximate tokens to keep (default: 4000)

    Returns:
        A history processor function that limits by token count
    """

    def processor(messages: List[ModelMessage]) -> List[ModelMessage]:
        # Rough approximation: 1 token ≈ 4 characters
        char_limit = max_tokens * 4

        # Start from the end and accumulate messages
        result = []
        char_count = 0

        for msg in reversed(messages):
            # Estimate message size
            msg_chars = len(str(msg))

            if char_count + msg_chars > char_limit and result:
                # Would exceed limit, stop here
                break

            result.insert(0, msg)
            char_count += msg_chars

        if len(result) < len(messages):
            logger.debug(
                f"Trimmed conversation history from {len(messages)} to {len(result)} "
                f"messages to stay within ~{max_tokens} tokens"
            )

        return result

    return processor
