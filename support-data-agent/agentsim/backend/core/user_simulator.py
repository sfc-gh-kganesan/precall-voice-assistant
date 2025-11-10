"""User simulator for generating realistic follow-up messages in conversations."""

import logging
from typing import List, Dict, Any, Optional
from backend.core.interfaces import Persona, ConversationMessage

logger = logging.getLogger(__name__)


class UserSimulator:
    """Simulates user responses in conversations based on persona."""

    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
    ):
        """Initialize user simulator.

        Args:
            provider: LLM provider (openai, anthropic, or snowflake)
            api_key: API key for the provider
            model: Model to use for generation
            base_url: Base URL for API (used for Snowflake Cortex)
        """
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client = None

    def _get_client(self):
        """Lazy load the LLM client."""
        if self._client is None:
            if self.provider == "openai":
                from openai import OpenAI

                self._client = OpenAI(api_key=self.api_key)
            elif self.provider == "snowflake":
                from openai import OpenAI

                # Use OpenAI client but point to Snowflake Cortex endpoint
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    max_retries=10,
                )
            elif self.provider == "anthropic":
                from anthropic import Anthropic

                self._client = Anthropic(api_key=self.api_key)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        return self._client

    async def generate_response(
        self,
        persona: Persona,
        conversation_history: List[ConversationMessage],
        agent_last_message: str,
        knowledge_base: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a realistic user response based on persona and conversation.

        Args:
            persona: The user persona with goals, tone, etc.
            conversation_history: Previous messages in the conversation
            agent_last_message: The agent's most recent response
            knowledge_base: Optional real data the persona has access to

        Returns:
            The simulated user's next message
        """
        # Build the prompt for the LLM
        system_prompt = self._build_system_prompt(persona, knowledge_base)
        user_prompt = self._build_user_prompt(conversation_history, agent_last_message)

        try:
            client = self._get_client()

            if self.provider in ["openai", "snowflake"]:
                # Snowflake Cortex uses max_completion_tokens instead of max_tokens
                token_param = (
                    "max_completion_tokens"
                    if self.provider == "snowflake"
                    else "max_tokens"
                )

                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.8,  # Higher temperature for more varied responses
                    **{token_param: 200},
                )
                return response.choices[0].message.content.strip()

            elif self.provider == "anthropic":
                response = client.messages.create(
                    model=self.model,
                    max_tokens=200,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    temperature=0.8,
                )
                return response.content[0].text.strip()

        except Exception as e:
            logger.error(f"Error generating user response: {e}")
            # Fallback to a simple response
            return self._generate_fallback_response(persona, agent_last_message)

    def _build_system_prompt(
        self, persona: Persona, knowledge_base: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build system prompt that defines the user persona."""
        # Build knowledge base section if provided
        knowledge_text = ""
        if knowledge_base:
            import json

            knowledge_text = f"""

IMPORTANT - YOU HAVE ACCESS TO THESE REAL DETAILS:
{json.dumps(knowledge_base, indent=2)}

When the agent asks for specific information (account numbers, query IDs, warehouses, etc.),
provide it naturally from the data above. Don't volunteer everything at once -
respond naturally to what is asked. If asked for data not in your knowledge base,
say you'll need to look it up or check.
"""

        return f"""You are simulating a user in a customer support conversation.

Your persona:
- Name: {persona.name}
- Goal: {persona.goal}
- Tone: {persona.tone}
- Personality: {", ".join(persona.personality_traits)}
- Technical Level: {persona.technical_level}
- Edge Case: {"Yes" if persona.edge_case else "No"}
{knowledge_text}
Important instructions:
1. Stay in character as this user throughout the conversation
2. Respond naturally based on what the agent just said
3. Keep responses concise (1-3 sentences)
4. Progress toward your goal: {persona.goal}
5. If the agent has resolved your issue, acknowledge it and thank them
6. If the agent asks a question, answer it from your persona's perspective
7. Match the tone: {persona.tone}
8. Don't break character or mention that you're simulating

Generate ONLY the user's next message, nothing else."""

    def _build_user_prompt(
        self, conversation_history: List[ConversationMessage], agent_last_message: str
    ) -> str:
        """Build the prompt with conversation context."""
        # Format conversation history
        history_text = ""
        if conversation_history:
            for msg in conversation_history[-6:]:  # Last 6 messages for context
                role_label = "You" if msg.role == "user" else "Agent"
                history_text += f"{role_label}: {msg.content}\n\n"

        prompt = f"""Here is the conversation so far:

{history_text}Agent: {agent_last_message}

Based on this conversation and your persona, what would you say next? Remember to stay in character.

Your response:"""

        return prompt

    def _generate_fallback_response(self, persona: Persona, agent_message: str) -> str:
        """Generate a simple fallback response if LLM fails."""
        # Check if agent is asking a question
        if "?" in agent_message:
            return "Yes, that sounds right."

        # Check if agent provided information
        if any(
            word in agent_message.lower()
            for word in ["here", "found", "shows", "data", "results"]
        ):
            return "Thank you, that's helpful!"

        # Check if agent is confirming resolution
        if any(
            word in agent_message.lower()
            for word in ["resolved", "fixed", "completed", "done"]
        ):
            return "Great, thank you for your help!"

        # Default follow-up
        if persona.tone == "frustrated":
            return "Is there anything else you can check?"
        elif persona.tone == "confused":
            return "I'm not sure I understand. Can you explain more?"
        else:
            return "Could you provide more details?"
