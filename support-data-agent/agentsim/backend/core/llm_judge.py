"""LLM-based judge for intelligent stop condition evaluation."""

import json
import logging
from typing import Optional
from backend.core.interfaces import (
    StopCondition,
    ConversationContext,
    ConversationMessage,
    StopReason,
)

logger = logging.getLogger(__name__)


class LLMStopCondition(StopCondition):
    """Use LLM to intelligently evaluate if conversation should stop."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = "openai-o4-mini",
        confidence_threshold: float = 0.8,
        max_retries: int = 2,
    ):
        """Initialize LLM stop condition.

        Args:
            api_key: Snowflake Cortex API key
            base_url: Snowflake Cortex base URL
            model: Model to use for evaluation
            confidence_threshold: Minimum confidence to stop (0.0-1.0)
            max_retries: Maximum retries on LLM failure
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.max_retries = max_retries
        self._client = None

    def _get_client(self):
        """Lazy load the LLM client."""
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                max_retries=self.max_retries,
            )
        return self._client

    def should_stop(
        self, context: ConversationContext, last_message: ConversationMessage
    ) -> tuple[bool, Optional[StopReason]]:
        """Use LLM to evaluate if conversation should stop.

        Args:
            context: Current conversation context
            last_message: Last message in conversation

        Returns:
            (should_stop, reason) tuple
        """
        # Only check after agent responses (not after user messages)
        if last_message.role != "assistant":
            return False, None

        try:
            evaluation = self._evaluate_with_llm(context, last_message)

            if evaluation["should_stop"] and evaluation["confidence"] >= self.confidence_threshold:
                logger.info(
                    f"LLM Judge recommends stopping conversation {context.conversation_id}: "
                    f"{evaluation['reasoning']} (confidence: {evaluation['confidence']:.2f})"
                )
                return True, StopReason.LLM_EVALUATION

            return False, None

        except Exception as e:
            logger.error(f"LLM stop condition evaluation failed: {e}", exc_info=True)
            # Fail open - don't stop on error
            return False, None

    def _evaluate_with_llm(
        self, context: ConversationContext, last_message: ConversationMessage
    ) -> dict:
        """Call LLM to evaluate conversation completion.

        Returns:
            Dict with keys: should_stop (bool), confidence (float), reasoning (str)
        """
        prompt = self._build_prompt(context, last_message)

        client = self._get_client()

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert conversation analyst. Evaluate if conversations have reached natural completion. Always respond with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=500,
            temperature=0.3,  # Lower temperature for more consistent evaluation
        )

        response_text = response.choices[0].message.content.strip()

        # Parse JSON response
        try:
            # Handle markdown code blocks
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()

            result = json.loads(response_text)

            # Validate response structure
            if "should_stop" not in result or "confidence" not in result:
                raise ValueError("Invalid response structure from LLM")

            # Ensure confidence is between 0 and 1
            result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))

            return result

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {e}. Response: {response_text}")
            # Default to not stopping on parse error
            return {
                "should_stop": False,
                "confidence": 0.0,
                "reasoning": "Failed to parse LLM response",
            }

    def _build_prompt(
        self, context: ConversationContext, last_message: ConversationMessage
    ) -> str:
        """Build evaluation prompt for the LLM."""
        # Format conversation history (last 10 messages for context)
        conversation_text = ""
        messages_to_include = context.messages[-10:]

        for msg in messages_to_include:
            role_label = "User" if msg.role == "user" else "Agent"
            conversation_text += f"{role_label}: {msg.content}\n\n"

        prompt = f"""Analyze this customer support conversation and determine if it has reached a natural completion point.

CONVERSATION (Turn {context.turn_count}):
{conversation_text}

Evaluate if the conversation should stop based on these criteria:
1. **Goal Achievement**: Has the user's issue/question been resolved?
2. **Agent Completeness**: Did the agent provide a complete, actionable response?
3. **User Satisfaction Signals**: Are there signs the user is satisfied? (e.g., "thank you", "that helps", "resolved")
4. **Conversation Flow**: Is the conversation wrapping up naturally, or are follow-ups expected?
5. **Information Completeness**: Has all necessary information been exchanged?

Consider that stopping is appropriate when:
- The user's goal has been clearly achieved
- The agent provided complete information/resolution
- The user expressed satisfaction or closure
- No obvious follow-up questions remain

Consider that continuing is appropriate when:
- The issue is partially resolved but needs more steps
- The agent asked a question waiting for user response
- The user indicated confusion or dissatisfaction
- Additional information gathering is needed

Respond ONLY with valid JSON in this format:
{{
  "should_stop": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of why the conversation should/shouldn't stop"
}}

Examples:
- If agent provided complete answer and user said "thank you": {{"should_stop": true, "confidence": 0.95, "reasoning": "User expressed satisfaction after receiving complete answer"}}
- If agent asked for more details: {{"should_stop": false, "confidence": 0.9, "reasoning": "Agent is waiting for user to provide requested information"}}
- If user says "that doesn't work": {{"should_stop": false, "confidence": 0.85, "reasoning": "User indicated the solution failed, needs troubleshooting"}}
"""

        return prompt
