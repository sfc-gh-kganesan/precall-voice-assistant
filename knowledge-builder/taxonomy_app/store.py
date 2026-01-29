"""
State management for Sunburst Push-Down Taxonomy application.
Follows React useReducer pattern with Pydantic for type safety.
"""

from typing import Annotated, Literal

import streamlit as st
from pydantic import BaseModel, Field


class Store(BaseModel):
    """Central state for the application."""

    # Taxonomy drill-down selection
    selected_l1: str | None = Field(default=None)
    selected_l2: str | None = Field(default=None)
    selected_l3: str | None = Field(default=None)
    selected_l4: str | None = Field(default=None)

    # Filter controls - empty means "all" (initialized from data on first load)
    source_types: list[str] = Field(default_factory=list)
    answerable_filter: list[str] = Field(default_factory=list)

    # AI-generated summary (on-demand)
    ai_summary: str | None = Field(default=None)
    ai_summary_loading: bool = Field(default=False)


# Action Types


class SetSelectedPathAction(BaseModel):
    """Set the selected path from sunburst click."""

    type: Literal["set_selected_path"] = "set_selected_path"
    l1: str | None = None
    l2: str | None = None
    l3: str | None = None
    l4: str | None = None


class ClearSelectionAction(BaseModel):
    """Clear all sunburst selections."""

    type: Literal["clear_selection"] = "clear_selection"


class SetSourceTypesAction(BaseModel):
    """Set which source types to include (incident/request)."""

    type: Literal["set_source_types"] = "set_source_types"
    source_types: list[str]


class SetAnswerableFilterAction(BaseModel):
    """Set answerable_with_kb filter values."""

    type: Literal["set_answerable_filter"] = "set_answerable_filter"
    values: list[str]


class InitializeFiltersAction(BaseModel):
    """Initialize filters from actual data options (first load only)."""

    type: Literal["initialize_filters"] = "initialize_filters"
    source_types: list[str]
    answerable_options: list[str]


class SetAISummaryAction(BaseModel):
    """Set the AI-generated knowledge gap summary."""

    type: Literal["set_ai_summary"] = "set_ai_summary"
    summary: str | None = None
    loading: bool = False


Action = Annotated[SetSelectedPathAction | ClearSelectionAction | SetSourceTypesAction | SetAnswerableFilterAction | InitializeFiltersAction | SetAISummaryAction, Field(discriminator="type")]


def reducer(state: Store, action: Action) -> Store:
    """Pure function to compute new state from action."""
    new_state = Store(**state.model_dump())

    if action.type == "set_selected_path":
        new_state.selected_l1 = action.l1
        new_state.selected_l2 = action.l2
        new_state.selected_l3 = action.l3
        new_state.selected_l4 = action.l4

    elif action.type == "clear_selection":
        new_state.selected_l1 = None
        new_state.selected_l2 = None
        new_state.selected_l3 = None
        new_state.selected_l4 = None

    elif action.type == "set_source_types":
        new_state.source_types = action.source_types

    elif action.type == "set_answerable_filter":
        new_state.answerable_filter = action.values

    elif action.type == "initialize_filters":
        # Only initialize if empty (first load)
        if not new_state.source_types:
            new_state.source_types = action.source_types
        if not new_state.answerable_filter:
            # Default to 'yes' to show cases that could be solved by knowledge base
            new_state.answerable_filter = ["yes"] if "yes" in action.answerable_options else action.answerable_options

    elif action.type == "set_ai_summary":
        new_state.ai_summary = action.summary
        new_state.ai_summary_loading = action.loading

    return new_state


def dispatch(action: Action) -> None:
    """Dispatch an action to update the store."""
    st.session_state.store = reducer(get_store(), action)


def get_store() -> Store:
    """Get the current store from session state."""
    if "store" not in st.session_state:
        st.session_state.store = Store()
    return st.session_state.store


def init_store() -> None:
    """Initialize the store in session state if not present."""
    if "store" not in st.session_state:
        st.session_state.store = Store()
