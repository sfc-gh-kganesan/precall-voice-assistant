# Phoenix Tracing Issues - TODO

## Current Situation

### What's Working ✓
- Backend is instrumented with OpenTelemetry
- Traces are being sent to Phoenix
- Pydantic AI configured with `InstrumentationSettings(version=2)` for GenAI semantic conventions
- Voice queries are processed and return results
- Text queries are processed and return results
- Message duplication in text chat UI is fixed

### What's Broken ❌
1. **Phoenix UI shows "--" for input/output columns** on all traces (both text and voice)
2. **Span hierarchy is disconnected for streaming requests**:
   - Text queries create TWO separate root spans: `api.query` (0ms) + `agent.run` (actual work)
   - They appear as siblings instead of parent-child relationship
3. **Voice queries may not be appearing in Phoenix** (last voice query didn't show up, but functionality worked)

## Root Cause Analysis

### The Core Problem: Async Generator Context Loss

**File**: `webagent/backend/external_agent_api.py` lines 341-437

When handling streaming requests (text queries):
```python
with tracer.start_as_current_span("api.query", ...) as span:  # Line 341
    # ... message parsing ...

    if request.stream:
        async def event_stream():
            # THIS RUNS LATER, OUTSIDE THE 'with' BLOCK
            async for event in agent.run_stream_events(message_text):
                # agent.run span is created here by Pydantic AI
                # But parent span (api.query) has already exited!

        return StreamingResponse(event_stream())  # Line 434
        # 'with' block exits HERE (span ends)
        # But StreamingResponse executes event_stream() LATER
```

**Result**:
- `api.query` span ends immediately (0ms latency)
- `agent.run` span executes later with no parent context
- They appear as disconnected root spans in Phoenix

### Why Phoenix Shows "--" for Input/Output

Phoenix expects GenAI semantic convention attributes on the **root span**:
- `gen_ai.input.messages` - JSON array of input messages
- `gen_ai.output.messages` - JSON array of output messages

**Current state**:
- Non-streaming (voice): Has attributes on `api.query` root span ✓
- Streaming (text): Has attributes on `agent.run` span ✓, but also creates disconnected `api.query` span
- Phoenix may be looking at the wrong span or getting confused by multiple roots

## Solution Options

### Option 1: Remove api.query span for streaming (SIMPLEST)
**Approach**: Only create `api.query` span for non-streaming requests

**Pros**:
- Simplest implementation (just move `with tracer.start_as_current_span()` into `else` block)
- No context propagation complexity
- Pydantic AI's instrumentation handles everything for streaming

**Cons**:
- ❌ Inconsistent trace structure (voice has `api.query` parent, text doesn't)
- ❌ Loss of API-level observability for streaming requests
- ❌ Can't see HTTP request handling time separately from agent execution
- ❌ Lose trace context propagation metadata (`traceparent`/`tracestate` from voice agent)
- ❌ Missing HTTP-level attributes (`conversation_id`, `triggered_by`, etc.)
- ❌ Harder to filter/query traces by endpoint

### Option 2: Manual span lifecycle management (PROPER FIX)
**Approach**: Don't use context manager for streaming; manually start/end span

**Implementation**:
```python
if request.stream:
    # Start span manually (don't use 'with')
    span = tracer.start_span("api.query", context=..., attributes=...)

    async def event_stream():
        # Capture span context at generator creation
        with trace.use_span(span, end_on_exit=False):
            # Now agent.run will be created as child of api.query
            async for event in agent.run_stream_events(...):
                yield ...

            # Add output attributes to parent span
            span.set_attribute("gen_ai.output.messages", ...)

        # End span when streaming completes
        span.end()

    return StreamingResponse(event_stream())
else:
    # Use context manager as normal for non-streaming
    with tracer.start_as_current_span("api.query", ...) as span:
        ...
```

**Pros**:
- ✓ Consistent trace hierarchy for all queries
- ✓ Proper parent-child relationship (api.query → agent.run)
- ✓ Full API-level observability
- ✓ Maintains trace context propagation
- ✓ All HTTP attributes preserved
- ✓ Easy to filter by endpoint in Phoenix

**Cons**:
- More complex code
- Manual span lifecycle management (risk of leaks if exceptions aren't handled)

### Option 3: Hybrid approach
**Approach**: Keep current structure but add explicit span links

Use OpenTelemetry span links to connect `api.query` and `agent.run` without parent-child relationship.

**Pros/Cons**: Middle ground complexity, but doesn't solve the "which span has GenAI attributes" problem.

## Recommended Solution

**For demo right now**: Option 1 (simplest)
**For production**: Option 2 (proper observability)

## Implementation Checklist

- [ ] Choose approach (Option 1 or 2)
- [ ] Implement code changes in `external_agent_api.py`
- [ ] Test with text query - verify single root span with input/output in Phoenix
- [ ] Test with voice query - verify proper span hierarchy
- [ ] Verify no disconnected/orphan spans
- [ ] Check Phoenix UI shows input/output in columns (not "--")
- [ ] Restart backend service
- [ ] Document final approach in code comments

## Files to Modify

- `webagent/backend/external_agent_api.py` (lines 307-442, `/query` endpoint)

## Testing Checklist

After implementing fix:
- [ ] Send text query via chat widget
- [ ] Check Phoenix: single root span (or proper parent-child)
- [ ] Check Phoenix: input column shows user message
- [ ] Check Phoenix: output column shows assistant response
- [ ] Send voice query
- [ ] Check Phoenix: trace appears
- [ ] Check Phoenix: proper span hierarchy (api.query → agent.run)
- [ ] Check Phoenix: input/output visible
- [ ] Verify no orphaned spans

## Questions to Resolve

1. **Priority**: Demo simplicity vs production observability?
2. **Trace structure**: OK to have different structures for voice vs text, or must be consistent?
3. **Trade-offs**: Acceptable to lose API-level observability for streaming in favor of simplicity?

## Related Context

- Phoenix expects GenAI semantic conventions at **root span level**
- Pydantic AI instrumentation creates `agent.run` span automatically with version=2 conventions
- Voice queries propagate trace context via W3C headers (`traceparent`/`tracestate`)
- Text queries use streaming path (`agent.run_stream_events()`)
- Non-streaming path works correctly (voice queries)
