# SDK Sync

Ensure parity between TypeScript and Python workflow SDKs when adding or modifying methods.

## Key Files

| Purpose | TypeScript | Python |
|---------|------------|--------|
| Public API / Interface | `packages/workflow-sdk/src/index.ts` | `packages/workflow-sdk-python/p67_sdk/sdk.py` |
| Types | `packages/workflow-sdk/src/index.ts` | `packages/workflow-sdk-python/p67_sdk/types.py` |
| Implementation | `services/controld/src/lib/sdk-impl.ts` | (same as sdk.py) |

## Workflow: Adding a New SDK Method

### Step 1: Define the TypeScript Interface

In `packages/workflow-sdk/src/index.ts`, add the method to the `WorkflowSDK` interface:

```typescript
export interface WorkflowSDK {
    // ... existing methods ...
    
    /**
     * Your method description
     * @param arg1 - Description
     * @returns Description
     */
    yourNewMethod(arg1: string, config_name?: string): Promise<YourResult>;
}
```

### Step 2: Add TypeScript Types

If the method needs new types, add them in the same file:

```typescript
export interface YourResult {
    success: boolean;
    data?: unknown;
    error?: string;
}
```

### Step 3: Implement in sdk-impl.ts

In `services/controld/src/lib/sdk-impl.ts`, implement the method:

```typescript
async yourNewMethod(arg1: string, config_name?: string): Promise<YourResult> {
    const cfg = this.cfg(config_name);
    // implementation
}
```

### Step 4: Add Python Types

In `packages/workflow-sdk-python/p67_sdk/types.py`:

```python
@dataclass
class YourResult:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
```

### Step 5: Implement in Python SDK

In `packages/workflow-sdk-python/p67_sdk/sdk.py`:

```python
def your_new_method(
    self,
    arg1: str,
    config_name: Optional[str] = None,
) -> YourResult:
    """
    Your method description.
    
    Args:
        arg1: Description
        config_name: Optional name of the config to use
        
    Returns:
        YourResult with success status
    """
    cfg = self._get_config(config_name)
    # implementation
```

## Naming Conventions

| TypeScript | Python |
|------------|--------|
| `camelCase` | `snake_case` |
| `executeQueryReadOnly` | `execute_query_read_only` |
| `config_name?: string` | `config_name: Optional[str] = None` |
| `Promise<T>` | Return type directly (blocking) |

## Current Public API Methods

Keep these in sync:

| TypeScript | Python | Status |
|------------|--------|--------|
| `getParameter(name, config_name?)` | `get_parameter(name, config_name=None)` | Sync |
| `getParameters(config_name?)` | `get_parameters(config_name=None)` | Sync |
| `executeQueryReadOnly(stmt, config_name?)` | `execute_query_read_only(sql_text, binds=None, config_name=None)` | Sync |
| `queryCortexAnalyst(question, semanticModel?, config_name?)` | `query_cortex_analyst(question, semantic_model=None, config_name=None)` | Sync |
| `callCortexAgent(question, options?, config_name?)` | `call_cortex_agent(question, options=None, config_name=None)` | Sync |
| `email(options, config_name?)` | `email(options, config_name=None)` | Sync |
| `httpRequest(options)` | `http_request(options)` | Sync |
| `interrupt(payload, options?)` | `interrupt(payload, options=None)` | Sync |
| `cortexComplete(options, config_name?)` | `cortex_complete(options, config_name=None)` | Sync |
| `cortexCompleteStream(options, config_name?)` | `cortex_complete_stream(options, config_name=None)` | Sync |
| `close()` | `close()` | Sync |

## Verification Checklist

When adding a new method, verify:

- [ ] Method exists in `WorkflowSDK` interface (TypeScript)
- [ ] Method implemented in `WorkflowSDKImpl` class (TypeScript)
- [ ] Method exists in `WorkflowSDK` class (Python)
- [ ] Types defined in both languages
- [ ] Docstrings match in both languages
- [ ] `config_name` parameter added if method uses Snowflake config
- [ ] Error handling follows same patterns (return error objects, don't throw)

## Quick Parity Check

Run this to compare public methods:

```bash
# TypeScript interface methods
grep -E '^\s+\w+\(' packages/workflow-sdk/src/index.ts | grep -v '//' | head -20

# Python class methods  
grep -E '^\s+def [a-z_]+\(' packages/workflow-sdk-python/p67_sdk/sdk.py | grep -v '_' | head -20
```

## Common Patterns

### Config Resolution
Both SDKs support:
- Single config: auto-selected when only one exists
- Named config: specify via `config_name` parameter
- Error if multiple configs exist and no name provided

### Error Handling
Return result objects instead of throwing:
```typescript
// TypeScript
return { success: false, error: 'message' };
```
```python
# Python
return YourResult(success=False, error='message')
```

### HTTP Requests
Both use native HTTP clients (fetch in TS, urllib in Python) with:
- Timeout support
- JSON serialization
- Bearer token injection for OAuth
