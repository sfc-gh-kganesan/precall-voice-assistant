"""LLM-based judge for analyzing simulations and generating improvement insights."""

import json
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.models.models import (
    Conversation,
    Message,
    ImprovementSuggestion,
    Simulation,
)

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
            simulation = (
                db.query(Simulation).filter(Simulation.id == simulation_id).first()
            )
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
            recommendations = await self._analyze_with_llm(
                simulation, conversations, db
            )

            # Deduplicate similar recommendations
            recommendations = self._deduplicate_recommendations(recommendations)

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
            logger.error(
                f"Failed to generate insights for simulation {simulation_id}: {e}",
                exc_info=True,
            )
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
            logger.error(
                f"Failed to parse LLM insights response: {e}. Response: {response_text}"
            )
            return []

    def _analyze_gaps(self, conversations: List[Conversation]) -> dict:
        """Analyze knowledge and capability gaps across conversations.

        Args:
            conversations: List of conversation records

        Returns:
            Dict with gap analysis and ending quality stats
        """
        from collections import defaultdict

        knowledge_gaps = defaultdict(list)
        capability_gaps = defaultdict(list)
        ending_stats = {"appropriate": 0, "premature": 0, "excessive": 0, "unknown": 0}

        for conv in conversations:
            # Extract evaluation data from scenario JSON
            evaluation = conv.scenario.get("evaluation", {}) if conv.scenario else {}

            # Track ending assessment
            ending = evaluation.get("ending_assessment", "unknown")
            ending_stats[ending] = ending_stats.get(ending, 0) + 1

            # Track knowledge gaps
            if kg := evaluation.get("knowledge_gap"):
                description = kg.get("description", "Unknown knowledge gap")
                gap_type = kg.get("type", "unknown")
                knowledge_gaps[f"[{gap_type}] {description}"].append(conv.id)

            # Track capability gaps
            if cg := evaluation.get("capability_gap"):
                description = cg.get("description", "Unknown capability gap")
                gap_type = cg.get("type", "unknown")
                capability_gaps[f"[{gap_type}] {description}"].append(conv.id)

        # Sort by frequency
        knowledge_gaps = dict(
            sorted(knowledge_gaps.items(), key=lambda x: len(x[1]), reverse=True)
        )
        capability_gaps = dict(
            sorted(capability_gaps.items(), key=lambda x: len(x[1]), reverse=True)
        )

        return {
            "knowledge_gaps": knowledge_gaps,
            "capability_gaps": capability_gaps,
            "ending_stats": ending_stats,
        }

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

            failed_examples.append(
                {
                    "conversation_id": conv.id,
                    "persona": conv.persona.get("name", "Unknown"),
                    "stop_reason": conv.stop_reason,
                    "turns": conv.num_turns,
                    "excerpt": conversation_text,
                }
            )

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

            success_examples.append(
                {
                    "conversation_id": conv.id,
                    "persona": conv.persona.get("name", "Unknown"),
                    "turns": conv.num_turns,
                    "excerpt": conversation_text,
                }
            )

        # Analyze gaps
        gap_analysis = self._analyze_gaps(conversations)

        # Format gap sections for prompt
        knowledge_gap_section = ""
        if gap_analysis["knowledge_gaps"]:
            knowledge_gap_section = "# KNOWLEDGE GAP ANALYSIS\n"
            for gap_desc, conv_ids in list(gap_analysis["knowledge_gaps"].items())[
                :10
            ]:  # Top 10
                knowledge_gap_section += f"- {gap_desc}: {len(conv_ids)} conversations (IDs: {conv_ids[:5]})\n"
        else:
            knowledge_gap_section = (
                "# KNOWLEDGE GAP ANALYSIS\nNo knowledge gaps detected.\n"
            )

        capability_gap_section = ""
        if gap_analysis["capability_gaps"]:
            capability_gap_section = "# CAPABILITY GAP ANALYSIS\n"
            for gap_desc, conv_ids in list(gap_analysis["capability_gaps"].items())[
                :10
            ]:  # Top 10
                capability_gap_section += f"- {gap_desc}: {len(conv_ids)} conversations (IDs: {conv_ids[:5]})\n"
        else:
            capability_gap_section = (
                "# CAPABILITY GAP ANALYSIS\nNo capability gaps detected.\n"
            )

        ending_stats = gap_analysis["ending_stats"]
        ending_section = f"""# CONVERSATION ENDING QUALITY
- Appropriate endings: {ending_stats.get("appropriate", 0)} ({ending_stats.get("appropriate", 0) / total_convs * 100:.1f}%)
- Premature endings (stopped too early): {ending_stats.get("premature", 0)} ({ending_stats.get("premature", 0) / total_convs * 100:.1f}%)
- Excessive conversations (went too long): {ending_stats.get("excessive", 0)} ({ending_stats.get("excessive", 0) / total_convs * 100:.1f}%)
- Unknown/Not evaluated: {ending_stats.get("unknown", 0)}
"""

        prompt = f"""Analyze this AI agent simulation and provide actionable improvement recommendations.

# SIMULATION OVERVIEW
- Total Conversations: {total_convs}
- Successful: {successful} ({successful / total_convs * 100:.1f}%)
- Failed: {failed} ({failed / total_convs * 100:.1f}%)
- Max Turns Setting: {simulation.max_turns}
- Timeout Setting: {simulation.timeout_seconds}s

# STOP REASONS BREAKDOWN
{json.dumps(stop_reasons, indent=2)}

# PERSONA PERFORMANCE
{json.dumps(persona_performance, indent=2)}

{knowledge_gap_section}

{capability_gap_section}

{ending_section}

# FAILED CONVERSATION EXAMPLES
{json.dumps(failed_examples, indent=2)}

# SUCCESSFUL CONVERSATION EXAMPLES
{json.dumps(success_examples, indent=2)}

# YOUR TASK
Analyze the above data and identify 5-10 specific, actionable improvements for this AI agent. Consider:

**IMPORTANT NOTE**: Conversations with stop_reason='historical_data' are pre-completed conversations
loaded from production logs for retrospective analysis. They did not go through AgentSmith's stop
condition logic. Do NOT recommend fixing "historical_data" stop reasons - this is an artifact of the
analysis methodology, not an agent behavior issue.

1. **Common Failure Patterns**: What's causing conversations to fail?
2. **Performance Issues**: Are there timeout or efficiency problems?
3. **Knowledge Gaps**: What information is missing from docs/KB? (See KNOWLEDGE GAP ANALYSIS above)
4. **Capability Gaps**: What tools/integrations are missing? (See CAPABILITY GAP ANALYSIS above)
5. **Conversation Ending**: Are conversations ending at appropriate times? (See ENDING QUALITY above)
6. **Logic Gaps**: Does the agent struggle with certain types of queries?
7. **UX Issues**: Is the agent's communication style effective?
8. **Error Handling**: How well does the agent handle edge cases?
9. **Persona-Specific Issues**: Does performance vary by user type?

PRIORITIZE recommendations based on:
- High-frequency capability gaps → Engineering team (new tools/integrations needed)
- High-frequency knowledge gaps → Documentation team (missing/incomplete docs)
- Premature endings → Prompt/logic improvements (agent giving up too early)
- Excessive conversations → Better completion detection (agent not recognizing resolution)

For each recommendation:
- **Category**: tool, knowledge, prompt, logic, error_handling, ux, or performance
- **Title**: Short, descriptive title (max 50 chars)
- **Description**: Detailed explanation of the issue and how to fix it (2-4 sentences)
- **Priority**: high (affects many conversations), medium, or low
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

    def _deduplicate_recommendations(
        self, recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Deduplicate similar recommendations by merging evidence.

        Args:
            recommendations: List of recommendation dicts from LLM

        Returns:
            Deduplicated list with merged evidence
        """
        if not recommendations:
            return recommendations

        from difflib import SequenceMatcher

        def similarity(a: str, b: str) -> float:
            """Calculate similarity ratio between two strings."""
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()

        deduplicated = []
        used_indices = set()

        for i, rec1 in enumerate(recommendations):
            if i in used_indices:
                continue

            # Find similar recommendations
            similar_group = [rec1]
            for j, rec2 in enumerate(recommendations[i + 1 :], start=i + 1):
                if j in used_indices:
                    continue

                # Check if similar: same category + (exact title OR high similarity)
                same_category = rec1.get("category") == rec2.get("category")
                title1 = rec1.get("title", "").strip().lower()
                title2 = rec2.get("title", "").strip().lower()
                exact_match = title1 == title2
                title_similarity = similarity(title1, title2)

                # Log comparison for debugging
                logger.debug(
                    f"Comparing insights: '{rec1.get('title')}' vs '{rec2.get('title')}' - "
                    f"Category match: {same_category}, Title similarity: {title_similarity:.2f}, Exact: {exact_match}"
                )

                # Consider duplicate if exact match OR >60% title similarity (lowered from 70%)
                if same_category and (exact_match or title_similarity > 0.6):
                    similar_group.append(rec2)
                    used_indices.add(j)
                    logger.info(
                        f"Found duplicate insight: '{rec2.get('title')}' matches '{rec1.get('title')}' "
                        f"(similarity: {title_similarity:.2f}, exact: {exact_match})"
                    )

            # Merge the group
            if len(similar_group) == 1:
                # No duplicates, keep as-is
                deduplicated.append(rec1)
            else:
                # Merge evidence from all similar recommendations
                merged = self._merge_recommendations(similar_group)
                deduplicated.append(merged)
                logger.info(
                    f"Merged {len(similar_group)} similar recommendations: '{merged['title']}'"
                )

        return deduplicated

    def _merge_recommendations(
        self, recommendations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge multiple similar recommendations into one.

        Args:
            recommendations: List of similar recommendations to merge

        Returns:
            Single merged recommendation
        """
        # Use the first as base
        merged = recommendations[0].copy()

        # Take highest priority
        priority_order = {"high": 3, "medium": 2, "low": 1}
        merged["priority"] = max(
            recommendations,
            key=lambda r: priority_order.get(r.get("priority", "low"), 0),
        )["priority"]

        # Merge evidence
        merged_evidence = {
            "conversation_ids": [],
            "affected_personas": [],
            "patterns": [],
            "metrics": {},
        }

        for rec in recommendations:
            evidence = rec.get("evidence", {})

            # Merge conversation IDs (union)
            conv_ids = evidence.get("conversation_ids", [])
            if conv_ids:
                merged_evidence["conversation_ids"].extend(conv_ids)

            # Merge personas (union)
            personas = evidence.get("affected_personas", [])
            if personas:
                merged_evidence["affected_personas"].extend(personas)

            # Collect patterns
            pattern = evidence.get("pattern")
            if pattern:
                merged_evidence["patterns"].append(pattern)

            # Merge metrics
            metrics = evidence.get("metrics", {})
            if metrics:
                merged_evidence["metrics"].update(metrics)

        # Deduplicate lists
        merged_evidence["conversation_ids"] = list(
            set(merged_evidence["conversation_ids"])
        )
        merged_evidence["affected_personas"] = list(
            set(merged_evidence["affected_personas"])
        )

        # Combine patterns into single pattern string
        if merged_evidence["patterns"]:
            merged_evidence["pattern"] = "; ".join(set(merged_evidence["patterns"]))
            del merged_evidence["patterns"]

        # Update counts
        if merged_evidence["conversation_ids"]:
            merged_evidence["conversation_count"] = len(
                merged_evidence["conversation_ids"]
            )
        if merged_evidence["affected_personas"]:
            merged_evidence["persona_count"] = len(merged_evidence["affected_personas"])

        merged["evidence"] = merged_evidence

        return merged
