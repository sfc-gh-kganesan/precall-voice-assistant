"""Scenario generator for creating synthetic test scenarios using LLMs."""

import json
import asyncio
from typing import List, Optional, Dict, Any
from backend.core.interfaces import Scenario, Persona
import openai
import anthropic


class ScenarioGenerator:
    """Generate test scenarios using LLM providers."""

    def __init__(
        self, provider: str = "openai", api_key: str = "", max_retries: int = 3
    ):
        """Initialize scenario generator.

        Args:
            provider: LLM provider ("openai" or "anthropic")
            api_key: API key for the provider
            max_retries: Maximum number of retries on failure
        """
        self.provider = provider
        self.api_key = api_key
        self.max_retries = max_retries

        if provider == "openai":
            self.client = openai.AsyncOpenAI(api_key=api_key)
        elif provider == "anthropic":
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
        elif provider == "snowflake":
            self.client = openai.AsyncOpenAI(api_key=api_key)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def generate_scenarios(
        self,
        business_context: str,
        num_scenarios: int,
        historical_conversations: Optional[List[Dict[str, Any]]] = None,
        edge_case_ratio: float = 0.2,
    ) -> List[Scenario]:
        """Generate test scenarios based on business context.

        Args:
            business_context: Description of the business/use case
            num_scenarios: Number of scenarios to generate
            historical_conversations: Optional historical conversation examples
            edge_case_ratio: Ratio of edge cases to generate (0.0-1.0)

        Returns:
            List of generated scenarios
        """
        prompt = self._build_prompt(
            business_context,
            num_scenarios,
            edge_case_ratio,
            historical_conversations,
        )

        for attempt in range(self.max_retries):
            try:
                response_text = await self._call_llm(prompt)
                scenarios = self._parse_llm_response(response_text)
                return scenarios[
                    :num_scenarios
                ]  # Ensure we return exactly num_scenarios
            except Exception:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2**attempt)  # Exponential backoff

        return []

    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM provider."""
        if (self.provider == "openai") or (self.provider == "snowflake"):
            response = await self.client.chat.completions.create(
                model="openai-o4-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that generates realistic test scenarios for AI agent testing. Always respond with valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,
            )
            return response.choices[0].message.content

        elif self.provider == "anthropic":
            response = await self.client.messages.create(
                model="claude-4-sonnet",
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,
            )
            return response.content[0].text

    def _build_prompt(
        self,
        business_context: str,
        num_scenarios: int,
        edge_case_ratio: float = 0.2,
        historical_conversations: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Build prompt for LLM."""
        num_edge_cases = int(num_scenarios * edge_case_ratio)
        num_common = num_scenarios - num_edge_cases

        prompt = f"""
Generate {num_scenarios} realistic test scenarios for an AI agent simulation.

Business Context: {business_context}

Requirements:
- Generate {num_common} common/typical scenarios
- Generate {num_edge_cases} edge case scenarios (unusual, complex, or adversarial)
- Each scenario should have a persona (user type) and an initial query
- Personas should vary in: tone, technical level, personality, and goals
- Make scenarios diverse across different categories and complexity levels
"""

        if historical_conversations:
            prompt += "\n\nHistorical Conversation Examples:\n"
            for i, conv in enumerate(
                historical_conversations[:3], 1
            ):  # Limit to 3 examples
                prompt += f"\nExample {i}:\n"
                for msg in conv:
                    prompt += f"{msg.get('role', 'user')}: {msg.get('content', '')}\n"

        prompt += """

Respond with a JSON object in this exact format:
{
  "personas": [
    {
      "name": "string",
      "goal": "string",
      "tone": "string (polite/frustrated/urgent/casual)",
      "personality_traits": ["string"],
      "technical_level": "string (beginner/intermediate/expert)",
      "edge_case": boolean
    }
  ],
  "scenarios": [
    {
      "initial_query": "string",
      "expected_outcome": "string (optional)",
      "complexity": "string (simple/moderate/complex)",
      "category": "string"
    }
  ]
}

Ensure personas and scenarios arrays have the same length and match by index.
"""
        return prompt

    def _parse_llm_response(self, response_text: str) -> List[Scenario]:
        """Parse LLM response into Scenario objects."""
        try:
            # Try to extract JSON if wrapped in markdown code blocks
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()

            data = json.loads(response_text)

            personas_data = data.get("personas", [])
            scenarios_data = data.get("scenarios", [])

            if len(personas_data) != len(scenarios_data):
                raise ValueError("Personas and scenarios count mismatch")

            scenarios = []
            for persona_data, scenario_data in zip(personas_data, scenarios_data):
                persona = Persona(
                    name=persona_data["name"],
                    goal=persona_data["goal"],
                    tone=persona_data["tone"],
                    personality_traits=persona_data["personality_traits"],
                    technical_level=persona_data["technical_level"],
                    edge_case=persona_data.get("edge_case", False),
                )

                scenario = Scenario(
                    persona=persona,
                    initial_query=scenario_data["initial_query"],
                    expected_outcome=scenario_data.get("expected_outcome"),
                    complexity=scenario_data["complexity"],
                    category=scenario_data["category"],
                )

                scenarios.append(scenario)

            return scenarios

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}")
        except KeyError as e:
            raise ValueError(f"Missing required field in response: {e}")
