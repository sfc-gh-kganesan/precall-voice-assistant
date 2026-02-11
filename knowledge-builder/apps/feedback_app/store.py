"""
State management for Feedback application.
Follows React useReducer pattern with Pydantic for type safety.
"""

from typing import Annotated, Literal

import streamlit as st
from pydantic import BaseModel, Field


class Store(BaseModel):
    """Central state for the application."""

    # Feedback tab state
    selected_input_type: str | None = Field(default=None)
    carousel_index: int = Field(default=0)  # Query-level carousel
    feedback_chunk_index: int = Field(default=0)  # Chunk-level carousel within a query

    # Playground state
    playground_query: str = Field(default="")
    playground_search_id: int | None = Field(default=None)
    playground_results: list = Field(default_factory=list)
    playground_chunk_index: int = Field(default=0)
    playground_agent_response: str | None = Field(default=None)

    # Filter state
    filters_initialized: bool = Field(default=False)


# Action Types


class SetInputTypeAction(BaseModel):
    """Set the selected input type filter."""

    type: Literal["set_input_type"] = "set_input_type"
    input_type: str | None = None


class SetCarouselIndexAction(BaseModel):
    """Set the current query carousel index."""

    type: Literal["set_carousel_index"] = "set_carousel_index"
    index: int = 0


class SetFeedbackChunkIndexAction(BaseModel):
    """Set the feedback chunk carousel index."""

    type: Literal["set_feedback_chunk_index"] = "set_feedback_chunk_index"
    index: int = 0


class SetPlaygroundResultsAction(BaseModel):
    """Set playground search results."""

    type: Literal["set_playground_results"] = "set_playground_results"
    query: str = ""
    search_id: int | None = None
    results: list = Field(default_factory=list)


class ClearPlaygroundAction(BaseModel):
    """Clear playground state."""

    type: Literal["clear_playground"] = "clear_playground"


class InitializeFiltersAction(BaseModel):
    """Initialize filters from data (first load only)."""

    type: Literal["initialize_filters"] = "initialize_filters"
    default_input_type: str | None = None


class SetPlaygroundChunkIndexAction(BaseModel):
    """Set the playground chunk carousel index."""

    type: Literal["set_playground_chunk_index"] = "set_playground_chunk_index"
    index: int = 0


class SetPlaygroundAgentResponseAction(BaseModel):
    """Cache the combined agent response."""

    type: Literal["set_playground_agent_response"] = "set_playground_agent_response"
    response: str | None = None


Action = Annotated[
    SetInputTypeAction | SetCarouselIndexAction | SetFeedbackChunkIndexAction | SetPlaygroundResultsAction | ClearPlaygroundAction | InitializeFiltersAction | SetPlaygroundChunkIndexAction | SetPlaygroundAgentResponseAction,
    Field(discriminator="type"),
]


def reducer(state: Store, action: Action) -> Store:
    """Pure function to compute new state from action."""
    new_state = Store(**state.model_dump())

    if action.type == "set_input_type":
        new_state.selected_input_type = action.input_type
        new_state.carousel_index = 0  # Reset query carousel when type changes
        new_state.feedback_chunk_index = 0  # Reset chunk carousel too

    elif action.type == "set_carousel_index":
        new_state.carousel_index = action.index
        new_state.feedback_chunk_index = 0  # Reset chunk carousel when query changes

    elif action.type == "set_feedback_chunk_index":
        new_state.feedback_chunk_index = action.index

    elif action.type == "set_playground_results":
        new_state.playground_query = action.query
        new_state.playground_search_id = action.search_id
        new_state.playground_results = action.results
        new_state.playground_chunk_index = 0  # Reset chunk carousel
        new_state.playground_agent_response = None  # Clear cached response

    elif action.type == "clear_playground":
        new_state.playground_query = ""
        new_state.playground_search_id = None
        new_state.playground_results = []
        new_state.playground_chunk_index = 0
        new_state.playground_agent_response = None

    elif action.type == "initialize_filters":
        if not new_state.filters_initialized:
            new_state.selected_input_type = action.default_input_type
            new_state.filters_initialized = True

    elif action.type == "set_playground_chunk_index":
        new_state.playground_chunk_index = action.index

    elif action.type == "set_playground_agent_response":
        new_state.playground_agent_response = action.response

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
