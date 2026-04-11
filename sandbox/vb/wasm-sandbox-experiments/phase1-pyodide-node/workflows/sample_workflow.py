"""
Sample P67-style workflow for testing in Pyodide.
Simplified version of the frostsight company_research workflow.
"""

async def fetch_company_data(state, sdk):
    """Fetch company data from database."""
    try:
        result = await sdk.execute_query(
            f"SELECT * FROM companies WHERE name = '{state['account_name']}'"
        )
        return {
            "sections": {"company_data": result.get("rows", [])},
            "status": "fetched"
        }
    except Exception as e:
        return {"errors": [f"fetch failed: {e}"], "status": "error"}


async def enrich_with_llm(state, sdk):
    """Enrich data using LLM."""
    try:
        data = state.get("sections", {}).get("company_data", [])
        response = await sdk.cortex_complete(
            model="claude-4-sonnet",
            messages=[{"role": "user", "content": f"Summarize: {data}"}]
        )
        summary = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {
            "sections": {**state.get("sections", {}), "summary": summary},
            "status": "enriched"
        }
    except Exception as e:
        return {"errors": [f"enrichment failed: {e}"], "status": "error"}


async def main(sdk):
    """Main workflow entry point."""
    params = sdk.get_parameters()
    account_name = params.get("account_name", "Unknown")

    state = {"account_name": account_name, "sections": {}, "errors": [], "status": "started"}

    state = {**state, **await fetch_company_data(state, sdk)}
    state = {**state, **await enrich_with_llm(state, sdk)}

    await sdk.close()

    return {"status": state["status"], "sections": state["sections"], "errors": state["errors"]}
