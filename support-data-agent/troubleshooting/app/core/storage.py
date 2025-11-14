"""Conversation history storage for agent memory management."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List

from pydantic_ai import ModelMessage

logger = logging.getLogger(__name__)


class ConversationStorage(ABC):
    """Abstract interface for storing conversation history."""

    @abstractmethod
    async def get_history(self, conversation_id: str) -> List[ModelMessage]:
        """Get conversation history for a given conversation ID."""
        pass

    @abstractmethod
    async def save_history(self, conversation_id: str, messages: List[ModelMessage]):
        """Save conversation history for a given conversation ID."""
        pass

    @abstractmethod
    async def clear_history(self, conversation_id: str):
        """Clear conversation history for a given conversation ID."""
        pass

    @abstractmethod
    async def list_conversations(self) -> List[str]:
        """List all conversation IDs with stored history."""
        pass


class InMemoryStorage(ConversationStorage):
    """In-memory storage implementation using a dictionary.

    Thread-safe implementation using asyncio.Lock.
    Note: Data is lost when the service restarts.
    """

    def __init__(self):
        self._conversations: Dict[str, List[ModelMessage]] = {}
        self._lock = asyncio.Lock()
        logger.info("Initialized InMemoryStorage for conversation history")

    async def get_history(self, conversation_id: str) -> List[ModelMessage]:
        """Get conversation history for a given conversation ID."""
        async with self._lock:
            history = self._conversations.get(conversation_id, [])
            logger.debug(
                f"Retrieved {len(history)} messages for conversation {conversation_id}"
            )
            return history.copy()  # Return copy to prevent external modifications

    async def save_history(self, conversation_id: str, messages: List[ModelMessage]):
        """Save conversation history for a given conversation ID."""
        async with self._lock:
            self._conversations[conversation_id] = messages.copy()
            logger.debug(
                f"Saved {len(messages)} messages for conversation {conversation_id}"
            )

    async def clear_history(self, conversation_id: str):
        """Clear conversation history for a given conversation ID."""
        async with self._lock:
            if conversation_id in self._conversations:
                del self._conversations[conversation_id]
                logger.info(f"Cleared history for conversation {conversation_id}")
            else:
                logger.warning(
                    f"Attempted to clear non-existent conversation {conversation_id}"
                )

    async def list_conversations(self) -> List[str]:
        """List all conversation IDs with stored history."""
        async with self._lock:
            return list(self._conversations.keys())


# Global storage instance
storage = InMemoryStorage()
