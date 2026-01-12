#!/usr/bin/env python
"""Run all cache experiments and compare results."""
import time
import json
from langchain_core.messages import HumanMessage

# Import all experiment graphs
from experiments.baseline.graph_llm import create_graph as create_baseline_graph
from experiments.plan_cache.graph_llm import create_graph as create_plan_cache_graph
from experiments.semantic_tool.graph_llm import create_tool_cache_graph
from experiments.semantic_full.graph_llm import create_full_cache_graph
from experiments.cortex_agent.run_cortex_agent import CortexAgentRunner

print("="*80)
print("CACHE EXPERIMENTS COMPARISON")
print("="*80)

# Load test dataset
with open('/tmp/cache_comparison_test.json', 'r') as f:
    data = json.load(f)
test_cases = data['test_cases']

print(f"\nRunning {len(test_cases)} test queries across 5 experiments...\n")

results = {}

# 1. Baseline (no caching)
print("1. Running BASELINE (no caching)...")
graph_baseline = create_baseline_graph()
start = time.time()
for tc in test_cases:
    state = {"messages": [HumanMessage(content=tc['query'])]}
    graph_baseline.invoke(state)
baseline_time = (time.time() - start) * 1000
results['baseline'] = {
    'time_ms': baseline_time,
    'plan_cache_hits': 0,
    'tool_cache_hits': 0,
    'total_cache_hits': 0
}
print(f"   Completed in {baseline_time:.0f}ms\n")

# 2. Plan Cache
print("2. Running PLAN CACHE (warmup + test)...")
graph_plan = create_plan_cache_graph(enable_cache=True, similarity_threshold=0.85)
# Warmup
for tc in test_cases:
    state = {"messages": [HumanMessage(content=tc['query'])], "cache_hit": False}
    graph_plan.invoke(state)
print("   Cache warmed up")
# Test with cache
plan_hits = 0
start = time.time()
for tc in test_cases:
    state = {"messages": [HumanMessage(content=tc['query'])], "cache_hit": False}
    result = graph_plan.invoke(state)
    if result.get('cache_hit', False):
        plan_hits += 1
plan_time = (time.time() - start) * 1000
results['plan_cache'] = {
    'time_ms': plan_time,
    'plan_cache_hits': plan_hits,
    'tool_cache_hits': 0,
    'total_cache_hits': plan_hits
}
print(f"   Completed in {plan_time:.0f}ms ({plan_hits}/{len(test_cases)} plan cache hits)\n")

# 3. Tool Cache
print("3. Running TOOL CACHE (warmup + test)...")
graph_tool = create_tool_cache_graph(cache_enabled=True, similarity_threshold=0.85)
# Warmup
for tc in test_cases:
    state = {
        "messages": [HumanMessage(content=tc['query'])],
        "tool_cache_hits": {},
        "cache_enabled": True
    }
    graph_tool.invoke(state)
print("   Cache warmed up")
# Test with cache
tool_hits = 0
start = time.time()
for tc in test_cases:
    state = {
        "messages": [HumanMessage(content=tc['query'])],
        "tool_cache_hits": {},
        "cache_enabled": True
    }
    result = graph_tool.invoke(state)
    # Count tool cache hits
    for tool_name, hits_list in result.get('tool_cache_hits', {}).items():
        tool_hits += sum(hits_list)
tool_time = (time.time() - start) * 1000
results['tool_cache'] = {
    'time_ms': tool_time,
    'plan_cache_hits': 0,
    'tool_cache_hits': tool_hits,
    'total_cache_hits': tool_hits
}
print(f"   Completed in {tool_time:.0f}ms ({tool_hits} tool cache hits)\n")

# 4. Full Cache (plan + tool)
print("4. Running FULL CACHE (warmup + test)...")
graph_full = create_full_cache_graph(
    enable_plan_cache=True,
    enable_tool_cache=True,
    similarity_threshold=0.85
)
# Warmup
for tc in test_cases:
    state = {
        "messages": [HumanMessage(content=tc['query'])],
        "plan_cache_hit": False,
        "tool_cache_hits": {},
        "cache_enabled": True
    }
    graph_full.invoke(state)
print("   Cache warmed up")
# Test with cache
full_plan_hits = 0
full_tool_hits = 0
start = time.time()
for tc in test_cases:
    state = {
        "messages": [HumanMessage(content=tc['query'])],
        "plan_cache_hit": False,
        "tool_cache_hits": {},
        "cache_enabled": True
    }
    result = graph_full.invoke(state)
    if result.get('plan_cache_hit', False):
        full_plan_hits += 1
    for tool_name, hits_list in result.get('tool_cache_hits', {}).items():
        full_tool_hits += sum(hits_list)
full_time = (time.time() - start) * 1000
results['full_cache'] = {
    'time_ms': full_time,
    'plan_cache_hits': full_plan_hits,
    'tool_cache_hits': full_tool_hits,
    'total_cache_hits': full_plan_hits + full_tool_hits
}
print(f"   Completed in {full_time:.0f}ms ({full_plan_hits} plan + {full_tool_hits} tool cache hits)\n")

# 5. Cortex Agent (Snowflake managed service)
print("5. Running CORTEX AGENT (Snowflake managed service)...")
cortex_runner = CortexAgentRunner()
start = time.time()
for tc in test_cases:
    cortex_runner.run_query(tc['query'])
cortex_time = (time.time() - start) * 1000
results['cortex_agent'] = {
    'time_ms': cortex_time,
    'plan_cache_hits': 0,  # N/A - managed service
    'tool_cache_hits': 0,  # N/A - managed service
    'total_cache_hits': 0
}
print(f"   Completed in {cortex_time:.0f}ms (managed service - internal caching not visible)\n")

# Print results table
print("="*80)
print("RESULTS COMPARISON")
print("="*80)
print("\n| Experiment      | Time (ms) | Plan Hits | Tool Hits | Total Hits | Speedup |")
print("|-----------------|-----------|-----------|-----------|------------|---------|")

for exp_name, metrics in results.items():
    speedup = baseline_time / metrics['time_ms'] if metrics['time_ms'] > 0 else 1.0
    print(f"| {exp_name:15s} | {metrics['time_ms']:9.0f} | "
          f"{metrics['plan_cache_hits']:9d} | {metrics['tool_cache_hits']:9d} | "
          f"{metrics['total_cache_hits']:10d} | {speedup:6.2f}x |")

print("\n" + "="*80)
print("✓ All experiments completed successfully!")
print("="*80)
