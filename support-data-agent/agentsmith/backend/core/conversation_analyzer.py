"""LLM-based analyzer for evaluating completed conversations."""

import json
import logging
from typing import Optional
from backend.core.interfaces import (
    ConversationContext,
    ConversationMessage,
)

logger = logging.getLogger(__name__)


class GapDetails:
    """Details about a detected gap in agent capabilities or knowledge."""

    def __init__(self, type: str, description: str, evidence: str):
        self.type = type
        self.description = description
        self.evidence = evidence

    def to_dict(self):
        return {
            "type": self.type,
            "description": self.description,
            "evidence": self.evidence,
        }


class ConversationEvaluation:
    """Evaluation results for a completed conversation."""

    def __init__(
        self,
        conversation_successful: bool,
        quality_score: float,
        confidence: float,
        ending_assessment: str,
        reasoning: str,
        knowledge_gap: Optional[GapDetails] = None,
        capability_gap: Optional[GapDetails] = None,
    ):
        self.conversation_successful = conversation_successful
        self.quality_score = quality_score
        self.confidence = confidence
        self.ending_assessment = ending_assessment
        self.reasoning = reasoning
        self.knowledge_gap = knowledge_gap
        self.capability_gap = capability_gap


class ConversationAnalyzer:
    """Analyze completed conversations for quality and identify gaps."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = "claude-4-sonnet",
        max_retries: int = 2,
    ):
        """Initialize conversation analyzer.

        Args:
            api_key: Snowflake Cortex API key (SNOWFLAKE_PASSWORD)
            base_url: Snowflake Cortex base URL
            model: Model to use for evaluation
            max_retries: Maximum retries on LLM failure
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
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

    async def evaluate_conversation(
        self, context: ConversationContext, all_messages: list[ConversationMessage]
    ) -> ConversationEvaluation:
        """Evaluate a completed conversation.

        Args:
            context: Conversation context
            all_messages: All messages in the conversation

        Returns:
            ConversationEvaluation with quality score and gap detection
        """
        try:
            evaluation_data = self._evaluate_with_llm(context, all_messages)

            # Parse knowledge gap if present
            knowledge_gap = None
            if kg := evaluation_data.get("knowledge_gap"):
                knowledge_gap = GapDetails(
                    type=kg.get("type", "unknown"),
                    description=kg.get("description", ""),
                    evidence=kg.get("evidence", ""),
                )

            # Parse capability gap if present
            capability_gap = None
            if cg := evaluation_data.get("capability_gap"):
                capability_gap = GapDetails(
                    type=cg.get("type", "unknown"),
                    description=cg.get("description", ""),
                    evidence=cg.get("evidence", ""),
                )

            return ConversationEvaluation(
                conversation_successful=evaluation_data.get(
                    "conversation_successful", False
                ),
                quality_score=float(evaluation_data.get("quality_score", 0.0)),
                confidence=float(evaluation_data.get("confidence", 0.0)),
                ending_assessment=evaluation_data.get("ending_assessment", "unknown"),
                reasoning=evaluation_data.get("reasoning", ""),
                knowledge_gap=knowledge_gap,
                capability_gap=capability_gap,
            )

        except Exception as e:
            logger.error(f"Conversation evaluation failed: {e}", exc_info=True)
            # Return default evaluation on error
            return ConversationEvaluation(
                conversation_successful=False,
                quality_score=0.0,
                confidence=0.0,
                ending_assessment="unknown",
                reasoning=f"Evaluation failed: {str(e)}",
            )

    def _evaluate_with_llm(
        self, context: ConversationContext, all_messages: list[ConversationMessage]
    ) -> dict:
        """Call LLM to evaluate conversation quality.

        Returns:
            Dict with evaluation results
        """
        prompt = self._build_prompt(context, all_messages)

        client = self._get_client()

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert conversation quality analyst. Evaluate completed customer support conversations and identify knowledge and capability gaps. Always respond with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=1000,
            temperature=0.3,  # Lower temperature for consistent evaluation
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
            required_fields = [
                "conversation_successful",
                "quality_score",
                "confidence",
                "ending_assessment",
                "reasoning",
            ]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")

            # Ensure scores are between 0 and 1
            result["quality_score"] = max(0.0, min(1.0, float(result["quality_score"])))
            result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))

            return result

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(
                f"Failed to parse LLM evaluation response: {e}. Response: {response_text}"
            )
            # Default to failed evaluation
            return {
                "conversation_successful": False,
                "quality_score": 0.0,
                "confidence": 0.0,
                "ending_assessment": "unknown",
                "reasoning": f"Failed to parse LLM response: {str(e)}",
            }

    def _build_prompt(
        self, context: ConversationContext, all_messages: list[ConversationMessage]
    ) -> str:
        """Build evaluation prompt for the LLM."""
        # Format full conversation history
        conversation_text = ""
        for msg in all_messages:
            role_label = "User" if msg.role == "user" else "Agent"
            conversation_text += f"{role_label}: {msg.content}\n\n"

        prompt = f"""You are analyzing a COMPLETED customer support conversation. Evaluate the quality and outcome of this conversation.

CONVERSATION ({len(all_messages)} messages, {context.turn_count} turns):
{conversation_text}

Evaluate this completed conversation on:

1. **Resolution Quality**: Was the user's issue fully resolved?
   - Did the agent provide a complete, actionable solution?
   - Were all user questions answered?

2. **Ending Appropriateness**: Did it end at the right time?
   - "appropriate": Ended at natural conclusion after resolution
   - "premature": Ended too early, user still had questions or issues
   - "excessive": Continued past resolution, unnecessary back-and-forth

3. **Agent Performance**: How well did the agent handle this?
   - Clear, helpful responses?
   - Professional and appropriate tone?

4. **Knowledge Gaps**: Did the agent lack necessary information?
   - **missing_documentation**: Expected information missing from docs/knowledge base
     * Agent says "I don't have information about X" for standard topics
     * Agent gives vague/uncertain answers where specific docs should exist
     * User asks about product features but agent can't explain them

   - **incomplete_knowledge_base**: Information exists but not in agent's context
     * Agent has general knowledge but lacks specifics
     * Recent changes/updates not reflected
     * Edge cases not covered

5. **Capability Gaps**: Did the agent lack necessary tools or abilities?
   - **missing_tool**: Agent cannot perform requested action
     * Examples: "I can't send emails", "I don't have access to create tickets"
     * User asks for action agent cannot execute

   - **missing_integration**: External system needed but not connected
     * Examples: "I can't access Jira", "No integration with Salesforce"
     * Agent references system but can't interact with it

   - **unsupported_action**: Functionality doesn't exist in the product
     * Examples: "Bulk export isn't available", "That feature isn't supported"
     * User requests capability that doesn't exist

When you detect a knowledge or capability gap, provide:
- **type**: The specific gap category
- **description**: One concise sentence explaining exactly what's missing
- **evidence**: Direct quote from conversation showing the gap

Respond ONLY with valid JSON in this format:
{{
  "conversation_successful": true/false,
  "quality_score": 0.0-1.0,
  "confidence": 0.0-1.0,
  "ending_assessment": "appropriate" | "premature" | "excessive",
  "reasoning": "Brief explanation of the evaluation",
  "knowledge_gap": {{
    "type": "missing_documentation" | "incomplete_knowledge_base",
    "description": "What information is missing",
    "evidence": "Quote from conversation"
  }},
  "capability_gap": {{
    "type": "missing_tool" | "missing_integration" | "unsupported_action",
    "description": "What action agent cannot perform",
    "evidence": "Quote from conversation"
  }}
}}

Note: Only include "knowledge_gap" and/or "capability_gap" if you detect them. Omit if not present.

Examples:

1. Successful conversation, no gaps:
{{
  "conversation_successful": true,
  "quality_score": 0.9,
  "confidence": 0.95,
  "ending_assessment": "appropriate",
  "reasoning": "User's login issue was resolved, agent provided clear steps, user confirmed it worked"
}}

2. Failed with capability gap:
{{
  "conversation_successful": false,
  "quality_score": 0.4,
  "confidence": 0.85,
  "ending_assessment": "premature",
  "reasoning": "User wanted email sent but agent lacks capability, conversation ended without resolution",
  "capability_gap": {{
    "type": "missing_tool",
    "description": "Agent cannot send emails on user's behalf",
    "evidence": "Agent said: 'I don't have the ability to send emails directly. You'll need to send it manually.'"
  }}
}}

3. Failed with knowledge gap:
{{
  "conversation_successful": false,
  "quality_score": 0.5,
  "confidence": 0.8,
  "ending_assessment": "excessive",
  "reasoning": "Agent couldn't answer pricing questions, conversation went in circles",
  "knowledge_gap": {{
    "type": "missing_documentation",
    "description": "Documentation lacks current Enterprise tier pricing information",
    "evidence": "Agent said: 'I don't have the latest pricing details for Enterprise plans'"
  }}
}}

Analyze the conversation above and provide your evaluation:"""

        return prompt
