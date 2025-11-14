"""LLM-based judge for analyzing simulations and generating improvement insights."""

import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.models.models import Conversation, Message, ImprovementSuggestion, Simulation

logger = logging.getLogger(__name__)


class InsightsJudge:
    """Analyze completed simulations to generate AI-powered improvement recommendations."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = "openai-gpt-4.1",
        max_retries: int = 2,
    ):
        """Initialize insights judge.

        Args:
            api_key: Snowflake Cortex API key
            base_url: Snowflake Cortex base URL
            model: Model to use for analysis
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

    async def generate_insights(
        self, simulation_id: int, db: Session
    ) -> List[ImprovementSuggestion]:
        """Generate AI-powered insights for a completed simulation.

        Args:
            simulation_id: ID of the completed simulation
            db: Database session

        Returns:
            List of ImprovementSuggestion objects
        """
        try:
            # Load simulation data
            simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
            if not simulation:
                raise ValueError(f"Simulation {simulation_id} not found")

            # Load all conversations
            conversations = (
                db.query(Conversation)
                .filter(Conversation.simulation_id == simulation_id)
                .all()
            )

            if not conversations:
                logger.warning(f"No conversations found for simulation {simulation_id}")
                return []

            # Analyze with LLM
            recommendations = await self._analyze_with_llm(simulation, conversations, db)

            # Create and save ImprovementSuggestion records
            suggestions = []
            for rec in recommendations:
                suggestion = ImprovementSuggestion(
                    simulation_id=simulation_id,
                    category=rec.get("category", "general"),
                    title=rec.get("title", "Untitled"),
                    description=rec.get("description", ""),
                    priority=rec.get("priority", "medium"),
                    evidence=rec.get("evidence", {}),
                )
                db.add(suggestion)
                suggestions.append(suggestion)

            db.commit()

            logger.info(
                f"Generated {len(suggestions)} AI-powered insights for simulation {simulation_id}"
            )
            return suggestions

        except Exception as e:
            logger.error(f"Failed to generate insights for simulation {simulation_id}: {e}", exc_info=True)
            db.rollback()
            return []

    async def _analyze_with_llm(
        self, simulation: Simulation, conversations: List[Conversation], db: Session
    ) -> List[Dict[str, Any]]:
        """Call LLM to analyze conversations and generate insights."""
        prompt = self._build_analysis_prompt(simulation, conversations, db)

        client = self._get_client()

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert AI agent analyst. Analyze agent performance and provide actionable improvement recommendations. Always respond with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=4000,
            temperature=0.4,
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
            if "recommendations" not in result:
                raise ValueError("Invalid response structure from LLM")

            return result["recommendations"]

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse LLM insights response: {e}. Response: {response_text}")
            return []

    def _build_analysis_prompt(
        self, simulation: Simulation, conversations: List[Conversation], db: Session
    ) -> str:
        """Build comprehensive analysis prompt for the LLM."""
        # Calculate statistics
        total_convs = len(conversations)
        successful = sum(1 for c in conversations if c.success)
        failed = total_convs - successful

        # Group by stop reason
        stop_reasons = {}
        for conv in conversations:
            reason = conv.stop_reason or "unknown"
            stop_reasons[reason] = stop_reasons.get(reason, 0) + 1

        # Group by persona type
        persona_performance = {}
        for conv in conversations:
            persona_name = conv.persona.get("name", "Unknown")
            if persona_name not in persona_performance:
                persona_performance[persona_name] = {"total": 0, "success": 0}
            persona_performance[persona_name]["total"] += 1
            if conv.success:
                persona_performance[persona_name]["success"] += 1

        # Sample failed conversations (up to 5)
        failed_convs = [c for c in conversations if not c.success][:5]
        failed_examples = []

        for conv in failed_convs:
            # Load messages for this conversation
            messages = (
                db.query(Message)
                .filter(Message.conversation_id == conv.id)
                .order_by(Message.timestamp)
                .all()
            )

            conversation_text = ""
            for msg in messages[:10]:  # Limit to first 10 messages
                role = "User" if msg.role == "user" else "Agent"
                conversation_text += f"{role}: {msg.content[:200]}...\n"

            failed_examples.append({
                "conversation_id": conv.id,
                "persona": conv.persona.get("name", "Unknown"),
                "stop_reason": conv.stop_reason,
                "turns": conv.num_turns,
                "excerpt": conversation_text
            })

        # Sample successful conversations (up to 3)
        success_convs = [c for c in conversations if c.success][:3]
        success_examples = []

        for conv in success_convs:
            messages = (
                db.query(Message)
                .filter(Message.conversation_id == conv.id)
                .order_by(Message.timestamp)
                .all()
            )

            conversation_text = ""
            for msg in messages[:10]:
                role = "User" if msg.role == "user" else "Agent"
                conversation_text += f"{role}: {msg.content[:200]}...\n"

            success_examples.append({
                "conversation_id": conv.id,
                "persona": conv.persona.get("name", "Unknown"),
                "turns": conv.num_turns,
                "excerpt": conversation_text
            })

        prompt = f"""Analyze this AI agent simulation and provide actionable improvement recommendations.

# SIMULATION OVERVIEW
- Total Conversations: {total_convs}
- Successful: {successful} ({successful/total_convs*100:.1f}%)
- Failed: {failed} ({failed/total_convs*100:.1f}%)
- Max Turns Setting: {simulation.max_turns}
- Timeout Setting: {simulation.timeout_seconds}s

# STOP REASONS BREAKDOWN
{json.dumps(stop_reasons, indent=2)}

# PERSONA PERFORMANCE
{json.dumps(persona_performance, indent=2)}

# FAILED CONVERSATION EXAMPLES
{json.dumps(failed_examples, indent=2)}

# SUCCESSFUL CONVERSATION EXAMPLES
{json.dumps(success_examples, indent=2)}

# YOUR TASK
Analyze the above data and identify 5-10 specific, actionable improvements for this AI agent. Consider:

1. **Common Failure Patterns**: What's causing conversations to fail?
2. **Performance Issues**: Are there timeout or efficiency problems?
3. **Logic Gaps**: Does the agent struggle with certain types of queries?
4. **UX Issues**: Is the agent's communication style effective?
5. **Tool Usage**: Are there missing capabilities or tools?
6. **Error Handling**: How well does the agent handle edge cases?
7. **Persona-Specific Issues**: Does performance vary by user type?

For each recommendation:
- **Category**: tool, prompt, logic, error_handling, ux, or performance
- **Title**: Short, descriptive title (max 50 chars)
- **Description**: Detailed explanation of the issue and how to fix it (2-4 sentences)
- **Priority**: high, medium, or low
- **Evidence**: Include conversation IDs, specific metrics, or patterns that support this recommendation

Respond ONLY with valid JSON in this format:
{{
  "recommendations": [
    {{
      "category": "string",
      "title": "string",
      "description": "string",
      "priority": "high|medium|low",
      "evidence": {{
        "conversation_ids": [123, 456],
        "affected_personas": ["Persona Name"],
        "metrics": {{"key": "value"}},
        "pattern": "description of observed pattern"
      }}
    }}
  ]
}}

Focus on recommendations that will have the biggest impact on success rate and user experience.
"""

        return prompt
