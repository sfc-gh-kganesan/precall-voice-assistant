# Synthetic Query Generation Guide

## Purpose

Synthetic queries bridge the gap between how a pattern is described (author's perspective) and how an engineer searches for it (problem-haver's perspective). Every query must describe a **problem an engineer would have before knowing this pattern exists**.

## Bad Query Examples

| Query | Why It's Bad |
|---|---|
| "How to use the PDF extraction pattern?" | Self-referential — assumes the engineer already knows the pattern |
| "PDF parsing" | Too vague — matches everything, helps nothing |
| "Pattern for LangGraph agent" | Describes the solution, not the problem |
| "What is OAuth token refresh?" | Definitional — engineer wouldn't search this way |

## Good Query Examples

### For a PDF Table Extraction Pattern:
- "How do I extract tables from multi-column PDFs?"
- "What's the best way to handle merged cells in PDF tables?"
- "How do I parse legal documents with nested table structures?"
- "My PDF extraction is missing rows — how do I handle spanning cells?"
- "How do I validate extracted table data against a known schema?"

### For an OAuth Token Refresh Pattern:
- "How do I keep my API connection alive during long batch jobs?"
- "My Snowflake token keeps expiring mid-pipeline — how do I handle refresh?"
- "How do I implement retry logic for authentication failures?"
- "What's the best way to manage token lifecycle in a multi-threaded service?"

### For a LangGraph Stateful Agent Pattern:
- "How do I route between multiple tools in a conversation agent?"
- "How do I maintain state across tool calls in LangGraph?"
- "My agent needs to pick the right tool dynamically — how do I implement that?"
- "How do I build a multi-step agent that remembers previous tool results?"

## Generation Rules

1. **Problem-first**: Frame as a problem, not a solution
2. **Specific**: Include domain terminology the engineer would use
3. **Varied**: Cover different angles — setup, debugging, scaling, edge cases
4. **Natural**: Write how an engineer would actually type in a search box
5. **5-10 queries per pattern**: Aim for breadth across use cases
