"""End-to-end test for AgentSim with Snowflake Cortex.

This script:
1. Starts the Cortex wrapper agent server
2. Starts the AgentSim API server
3. Creates a project configured to talk to the Cortex agent
4. Runs a simulation with support data queries
5. Displays results

Run with: uv run test_cortex_e2e.py
"""

import asyncio
import subprocess
import time
import httpx
import sys
from typing import Optional

# Configuration
CORTEX_AGENT_PORT = 8002
AGENTSIM_PORT = 8000
CORTEX_AGENT_URL = f"http://localhost:{CORTEX_AGENT_PORT}"
AGENTSIM_URL = f"http://localhost:{AGENTSIM_PORT}"


class ServerManager:
    """Manages server processes for testing."""

    def __init__(self):
        self.cortex_agent_process: Optional[subprocess.Popen] = None
        self.agentsim_process: Optional[subprocess.Popen] = None

    def start_cortex_agent(self):
        """Start the Cortex wrapper agent server."""
        print(f"🚀 Starting Cortex agent wrapper on port {CORTEX_AGENT_PORT}...")
        self.cortex_agent_process = subprocess.Popen(
            [sys.executable, "cortex_wrapper_agent.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(3)  # Give it time to start and connect to Snowflake

    def start_agentsim(self):
        """Start the AgentSim API server."""
        print(f"🚀 Starting AgentSim API server on port {AGENTSIM_PORT}...")
        self.agentsim_process = subprocess.Popen(
            [
                "uvicorn",
                "backend.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                str(AGENTSIM_PORT),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(3)  # Give it time to start

    async def wait_for_health(self, url: str, max_attempts: int = 30) -> bool:
        """Wait for a server to be healthy."""
        async with httpx.AsyncClient() as client:
            for i in range(max_attempts):
                try:
                    response = await client.get(f"{url}/health", timeout=2.0)
                    if response.status_code == 200:
                        return True
                except (httpx.ConnectError, httpx.TimeoutException):
                    if i < max_attempts - 1:
                        await asyncio.sleep(1)
            return False

    def cleanup(self):
        """Stop all servers."""
        print("\n🛑 Stopping servers...")
        if self.cortex_agent_process:
            self.cortex_agent_process.terminate()
            self.cortex_agent_process.wait()
        if self.agentsim_process:
            self.agentsim_process.terminate()
            self.agentsim_process.wait()


async def create_project(client: httpx.AsyncClient) -> int:
    """Create a test project pointing to Cortex agent."""
    print("\n📋 Creating test project...")

    project_data = {
        "name": "Cortex E2E Test Project",
        "description": "End-to-end test of AgentSim with Snowflake Cortex agent",
        "business_context": """
        This is a customer support agent data analyst powered by Snowflake Cortex.
        The agent can answer questions about:
        - Support case volumes and trends
        - Product categories and ticket distribution
        - Case priorities and escalations
        - Historical support metrics

        The agent has access to a support database via Cortex Analyst and can
        generate SQL queries to answer data-related questions.
        """,
        "agent_endpoint": f"{CORTEX_AGENT_URL}/api/chat",
        "auth_type": "none",
        "auth_credentials": {},
        "custom_headers": None,
        "conversation_examples": None,
    }

    response = await client.post(f"{AGENTSIM_URL}/api/projects/", json=project_data)
    response.raise_for_status()
    project = response.json()
    project_id = project["id"]
    print(f"✅ Created project with ID: {project_id}")
    return project_id


async def run_simulation(client: httpx.AsyncClient, project_id: int) -> int:
    """Run a simulation with support data queries."""
    print("\n🔬 Starting simulation...")

    # Example custom personas for testing Cortex support agent
    custom_scenarios = [
        {
            "persona": {
                "name": "Frustrated Data Analyst",
                "goal": "Get Q4 2023 support case metrics urgently",
                "tone": "urgent",
                "personality_traits": ["impatient", "technical", "direct"],
                "technical_level": "expert",
                "edge_case": False,
            },
            "initial_query": "I need Q4 2023 support case data RIGHT NOW for my exec presentation!",
            "expected_outcome": "Receive accurate Q4 2023 support metrics",
            "complexity": "simple",
            "category": "data_query",
        },
        {
            "persona": {
                "name": "Confused Manager",
                "goal": "Understand product categories with most support issues",
                "tone": "polite",
                "personality_traits": ["non-technical", "methodical", "appreciative"],
                "technical_level": "beginner",
                "edge_case": False,
            },
            "initial_query": "Hi, I'm trying to figure out which of our products need the most help. Can you show me?",
            "expected_outcome": "Clear explanation of product support distribution",
            "complexity": "moderate",
            "category": "product_analysis",
        },
        {
            "persona": {
                "name": "Systematic QA Engineer",
                "goal": "Validate case priority distribution for testing",
                "tone": "professional",
                "personality_traits": ["detail-oriented", "systematic", "thorough"],
                "technical_level": "intermediate",
                "edge_case": False,
            },
            "initial_query": "I need to verify the priority distribution of support cases for our QA baseline",
            "expected_outcome": "Detailed breakdown of case priorities with counts",
            "complexity": "moderate",
            "category": "quality_assurance",
        },
    ]

    simulation_data = {
        "project_id": project_id,
        "num_simulations": 3,  # Will be overridden by custom_scenarios length
        "concurrency": 4,  # Sequential for easier debugging
        "max_turns": 20,  # Allow longer conversations for realistic multi-turn dialogue
        "timeout_seconds": 120,  # Generous timeout for Cortex API
        "stop_conditions": ["max_turns", "agent_signal"],
        "metrics_config": ["efficiency", "quality"],
        "custom_scenarios": custom_scenarios,  # Use our custom personas
    }

    response = await client.post(
        f"{AGENTSIM_URL}/api/simulations/", json=simulation_data
    )
    response.raise_for_status()
    simulation = response.json()
    simulation_id = simulation["id"]
    print(f"✅ Started simulation with ID: {simulation_id}")
    print(f"   Status: {simulation['status']}")
    print(f"   Using {len(custom_scenarios)} custom personas")
    return simulation_id


async def wait_for_simulation(
    client: httpx.AsyncClient, simulation_id: int, max_wait: int = 900
):
    """Wait for simulation to complete with live progress tracking."""
    print("\n⏳ Waiting for simulation to complete...")
    print("   (This may take a while as Cortex processes queries)")

    start_time = time.time()
    last_status = None
    last_update = {}  # Track last seen state per conversation

    # Get total expected conversations
    response = await client.get(f"{AGENTSIM_URL}/api/simulations/{simulation_id}")
    response.raise_for_status()
    simulation = response.json()
    total_conversations = simulation.get("num_simulations", 0)

    while time.time() - start_time < max_wait:
        # Get simulation status
        response = await client.get(f"{AGENTSIM_URL}/api/simulations/{simulation_id}")
        response.raise_for_status()
        simulation = response.json()

        status = simulation["status"]
        if status != last_status:
            print(f"   Status: {status}")
            last_status = status

        if status in ["completed", "failed"]:
            return simulation

        # If running, get live progress
        if status == "running":
            try:
                # Get all conversations (completed and in-progress)
                conv_response = await client.get(
                    f"{AGENTSIM_URL}/api/simulations/{simulation_id}/conversations"
                )
                conv_response.raise_for_status()
                conversations = conv_response.json()

                elapsed = int(time.time() - start_time)

                # Separate completed and in-progress conversations
                completed_convs = [
                    c for c in conversations if c.get("completed_at") is not None
                ]
                in_progress_convs = [
                    c for c in conversations if c.get("completed_at") is None
                ]

                # Show update for each conversation that has new activity
                for conv in conversations:
                    conv_id = conv["id"]
                    persona_name = conv.get("persona", {}).get("name", "Unknown")
                    turns = conv.get("num_turns", 0)
                    is_completed = conv.get("completed_at") is not None

                    # Create state key to detect changes
                    state_key = f"{conv_id}_{turns}_{is_completed}"

                    if state_key != last_update.get(conv_id):
                        last_update[conv_id] = state_key

                        # Only show updates for Turn 1, every 3 turns, or completion
                        should_show = (turns == 1) or (turns % 3 == 0) or is_completed

                        if should_show:
                            # Fetch latest messages for this conversation
                            try:
                                msg_response = await client.get(
                                    f"{AGENTSIM_URL}/api/conversations/{conv_id}"
                                )
                                msg_response.raise_for_status()
                                full_conv = msg_response.json()
                                messages = full_conv.get("messages", [])

                                if is_completed:
                                    # Completed conversation
                                    duration_sec = (
                                        conv.get("total_duration_ms", 0) / 1000
                                    )
                                    success_icon = "✅" if conv.get("success") else "❌"
                                    print(
                                        f"\n   {success_icon} Completed: {persona_name} - {turns} turns, {duration_sec:.1f}s [Elapsed: {elapsed}s]"
                                    )
                                else:
                                    # In-progress conversation
                                    print(
                                        f"\n   🔄 In Progress: {persona_name} - Turn {turns} [Elapsed: {elapsed}s]"
                                    )

                                # Show latest Q&A
                                if messages:
                                    user_msgs = [
                                        m for m in messages if m["role"] == "user"
                                    ]
                                    assistant_msgs = [
                                        m for m in messages if m["role"] == "assistant"
                                    ]

                                    if user_msgs:
                                        last_user = user_msgs[-1]["content"][:150]
                                        print(f"      👤 Last Q: {last_user}...")

                                    if assistant_msgs:
                                        last_assistant = assistant_msgs[-1]["content"][
                                            :150
                                        ]
                                        print(f"      🤖 Last A: {last_assistant}...")

                            except Exception:
                                # Don't break on message fetch errors
                                pass

                # Show progress summary
                if len(completed_convs) + len(in_progress_convs) > 0:
                    progress_line = f"   Progress: {len(completed_convs)} completed"
                    if in_progress_convs:
                        progress_line += f", {len(in_progress_convs)} in progress"
                    progress_line += f" of {total_conversations} total"
                    # Only print if this is new info
                    if progress_line not in last_update.get("summary", ""):
                        last_update["summary"] = progress_line

            except Exception:
                # Don't break on progress fetch errors
                pass

        await asyncio.sleep(2)  # Check every 2 seconds for faster updates

    raise TimeoutError("Simulation did not complete in time")


async def get_results(client: httpx.AsyncClient, simulation_id: int):
    """Get and display simulation results."""
    print("\n📊 Fetching results...")

    response = await client.get(
        f"{AGENTSIM_URL}/api/simulations/{simulation_id}/results"
    )
    if response.status_code == 400:
        print("⚠️  Simulation not completed yet or no results available")
        return None

    response.raise_for_status()
    results = response.json()

    print("\n" + "=" * 60)
    print("CORTEX SIMULATION RESULTS")
    print("=" * 60)
    print(f"Simulation ID: {results['id']}")
    print(f"Project ID: {results['project_id']}")
    print(f"Total Simulations: {results['num_simulations']}")
    print(f"Status: {results['status']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    print(
        f"Success Rate: {results['successful'] / results['num_simulations'] * 100:.1f}%"
    )
    print("\nAggregate Metrics:")
    for metric_name, value in results.get("aggregate_metrics", {}).items():
        if isinstance(value, float):
            print(f"  {metric_name}: {value:.2f}")
        else:
            print(f"  {metric_name}: {value}")
    print("=" * 60)

    return results


async def get_conversations(client: httpx.AsyncClient, simulation_id: int):
    """Get and display conversation details."""
    print("\n💬 Fetching conversation details...")

    response = await client.get(
        f"{AGENTSIM_URL}/api/simulations/{simulation_id}/conversations"
    )
    response.raise_for_status()
    conversations = response.json()

    print(f"\nFound {len(conversations)} conversations")
    print("=" * 80)

    # Show first conversation in detail
    if conversations:
        conv = conversations[0]
        print(f"\n📝 Sample Conversation (ID: {conv['id']})")
        print(f"   Success: {'✅' if conv['success'] else '❌'}")
        print(f"   Turns: {conv['num_turns']}")
        print(f"   Duration: {conv['total_duration_ms']:.0f}ms")
        print(f"   Stop Reason: {conv['stop_reason']}")

        # Get full conversation with messages
        response = await client.get(f"{AGENTSIM_URL}/api/conversations/{conv['id']}")
        response.raise_for_status()
        full_conv = response.json()

        print("\n   Scenario:")
        print(f"   {full_conv.get('scenario', {}).get('initial_query', 'N/A')}")

        print("\n   Messages:")
        print("   " + "-" * 76)
        for msg in full_conv.get("messages", []):
            role_icon = "👤" if msg["role"] == "user" else "🤖"
            print(f"\n   {role_icon} {msg['role'].upper()}:")
            # Truncate long messages for display
            content = msg["content"]
            if len(content) > 200:
                content = content[:200] + "..."
            print(f"   {content}")
            if msg.get("latency_ms"):
                print(f"   ⏱️  {msg['latency_ms']:.0f}ms")

    print("\n" + "=" * 80)

    # Show summary of all conversations
    print("\n📊 All Conversations Summary:")
    print(
        f"{'ID':<8} {'Success':<10} {'Turns':<8} {'Duration':<12} {'Stop Reason':<15}"
    )
    print("-" * 80)
    for conv in conversations:
        success_str = "✅ Yes" if conv["success"] else "❌ No"
        print(
            f"{conv['id']:<8} {success_str:<10} {conv['num_turns']:<8} {conv['total_duration_ms']:<12.0f} {conv['stop_reason']:<15}"
        )
    print("=" * 80)

    # Multi-turn analysis
    print("\n🔄 MULTI-TURN CONVERSATION ANALYSIS")
    print("=" * 80)
    total_turns = sum(c["num_turns"] for c in conversations)
    avg_turns = total_turns / len(conversations) if conversations else 0
    multi_turn_count = sum(1 for c in conversations if c["num_turns"] > 1)

    print("\n📈 Multi-Turn Metrics:")
    print(f"   Total conversations: {len(conversations)}")
    print(f"   Average turns per conversation: {avg_turns:.1f}")
    print(
        f"   Conversations with multiple turns: {multi_turn_count} ({multi_turn_count / len(conversations) * 100:.0f}%)"
    )
    print(
        f"   Multi-turn enabled: {'✅ YES - User simulator is generating follow-ups!' if avg_turns > 1.5 else '⚠️  PARTIAL - Some single-turn conversations' if avg_turns > 1.0 else '❌ NO - Still single turn only'}"
    )

    if avg_turns > 1.5:
        print("\n✨ Success! The Snowflake Cortex user simulator is working correctly.")
        print("   Conversations are having realistic back-and-forth dialogue.")

    print("=" * 80)


async def main():
    """Run the end-to-end test with Cortex."""
    # Kill any existing servers on the ports first
    print("🧹 Cleaning up any existing servers...")
    subprocess.run(
        ["lsof", "-ti", f":{CORTEX_AGENT_PORT}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    subprocess.run(
        f"lsof -ti:{CORTEX_AGENT_PORT} | xargs kill -9 2>/dev/null || true",
        shell=True,
        check=False,
    )
    subprocess.run(
        f"lsof -ti:{AGENTSIM_PORT} | xargs kill -9 2>/dev/null || true",
        shell=True,
        check=False,
    )
    time.sleep(1)

    server_manager = ServerManager()

    try:
        # Start servers
        server_manager.start_cortex_agent()
        server_manager.start_agentsim()

        # Wait for servers to be healthy
        print("\n⏳ Waiting for servers to be ready...")
        async with httpx.AsyncClient() as client:
            cortex_healthy = await server_manager.wait_for_health(CORTEX_AGENT_URL)
            agentsim_healthy = await server_manager.wait_for_health(AGENTSIM_URL)

            if not cortex_healthy:
                print("❌ Cortex agent server failed to start")
                print("   Check that Snowflake credentials are configured in .env")
                return
            print(f"✅ Cortex agent is healthy at {CORTEX_AGENT_URL}")

            if not agentsim_healthy:
                print("❌ AgentSim API server failed to start")
                return
            print(f"✅ AgentSim API is healthy at {AGENTSIM_URL}")

        # Run the test workflow
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create project
            project_id = await create_project(client)

            # Run simulation
            simulation_id = await run_simulation(client, project_id)

            # Wait for completion
            simulation = await wait_for_simulation(client, simulation_id)

            if simulation["status"] == "completed":
                print("\n✅ Simulation completed successfully!")
                # Get results
                await get_results(client, simulation_id)
                # Get conversation details
                await get_conversations(client, simulation_id)
            else:
                print(
                    f"\n❌ Simulation failed: {simulation.get('error_message', 'Unknown error')}"
                )

        print("\n✅ End-to-end Cortex test completed!")
        print(
            "\nNote: Check the AgentSim database for detailed conversation logs and metrics."
        )

    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback

        traceback.print_exc()
    finally:
        server_manager.cleanup()
        print("✅ Cleanup complete")


if __name__ == "__main__":
    asyncio.run(main())
