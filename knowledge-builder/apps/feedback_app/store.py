"""State management for Feedback application using Redux-style reducer pattern."""

from typing import Annotated, Literal

import streamlit as st
from pydantic import BaseModel, Field


class Store(BaseModel):
    """Central state for the application."""

    selected_input_types: tuple[str, ...] = Field(default_factory=tuple)
    carousel_index: int = Field(default=0)
    feedback_chunk_index: int = Field(default=0)
    feedback_article_index: int = Field(default=0)

    playground_query: str = Field(default="")
    playground_search_id: int | None = Field(default=None)
    playground_results: list = Field(default_factory=list)
    playground_chunk_index: int = Field(default=0)
    playground_article_index: int = Field(default=0)
    playground_agent_response: str | None = Field(default=None)

    # Feedback tab agent response (keyed by search_id, cached here)
    feedback_agent_response: str | None = Field(default=None)
    feedback_agent_response_search_id: int | None = Field(default=None)

    filters_initialized: bool = Field(default=False)


class SetInputTypesAction(BaseModel):
    """Set the selected input types filter."""

    type: Literal["set_input_types"] = "set_input_types"
    input_types: tuple[str, ...] = Field(default_factory=tuple)


class SetCarouselIndexAction(BaseModel):
    """Set the current query carousel index."""

    type: Literal["set_carousel_index"] = "set_carousel_index"
    index: int = 0


class SetFeedbackChunkIndexAction(BaseModel):
    """Set the feedback chunk carousel index."""

    type: Literal["set_feedback_chunk_index"] = "set_feedback_chunk_index"
    index: int = 0


class SetFeedbackArticleIndexAction(BaseModel):
    """Set the feedback article carousel index."""

    type: Literal["set_feedback_article_index"] = "set_feedback_article_index"
    index: int = 0


class SetPlaygroundResultsAction(BaseModel):
    """Set playground search results."""

    type: Literal["set_playground_results"] = "set_playground_results"
    query: str = ""
    search_id: int | None = None
    results: list = Field(default_factory=list)


class InitializeFiltersAction(BaseModel):
    """Initialize filters from data (first load only)."""

    type: Literal["initialize_filters"] = "initialize_filters"
    default_input_types: tuple[str, ...] = Field(default_factory=tuple)


class SetPlaygroundChunkIndexAction(BaseModel):
    """Set the playground chunk carousel index."""

    type: Literal["set_playground_chunk_index"] = "set_playground_chunk_index"
    index: int = 0


class SetPlaygroundArticleIndexAction(BaseModel):
    """Set the playground article carousel index."""

    type: Literal["set_playground_article_index"] = "set_playground_article_index"
    index: int = 0


class SetPlaygroundAgentResponseAction(BaseModel):
    """Cache the combined agent response."""

    type: Literal["set_playground_agent_response"] = "set_playground_agent_response"
    response: str | None = None


class SetFeedbackAgentResponseAction(BaseModel):
    """Cache the feedback tab agent response for a specific search."""

    type: Literal["set_feedback_agent_response"] = "set_feedback_agent_response"
    search_id: int | None = None
    response: str | None = None


Action = Annotated[
    SetInputTypesAction | SetCarouselIndexAction | SetFeedbackChunkIndexAction | SetFeedbackArticleIndexAction | SetPlaygroundResultsAction | InitializeFiltersAction | SetPlaygroundChunkIndexAction | SetPlaygroundArticleIndexAction | SetPlaygroundAgentResponseAction | SetFeedbackAgentResponseAction,
    Field(discriminator="type"),
]


def reducer(state: Store, action: Action) -> Store:
    """Pure function to compute new state from action."""
    new_state = Store(**state.model_dump())

    if action.type == "set_input_types":
        new_state.selected_input_types = action.input_types
        new_state.carousel_index = 0
        new_state.feedback_chunk_index = 0
        new_state.feedback_article_index = 0

    elif action.type == "set_carousel_index":
        new_state.carousel_index = action.index
        new_state.feedback_chunk_index = 0
        new_state.feedback_article_index = 0
        # Reset agent response when changing queries
        new_state.feedback_agent_response = None
        new_state.feedback_agent_response_search_id = None

    elif action.type == "set_feedback_chunk_index":
        new_state.feedback_chunk_index = action.index

    elif action.type == "set_feedback_article_index":
        new_state.feedback_article_index = action.index

    elif action.type == "set_playground_results":
        new_state.playground_query = action.query
        new_state.playground_search_id = action.search_id
        new_state.playground_results = action.results
        new_state.playground_chunk_index = 0
        new_state.playground_article_index = 0
        new_state.playground_agent_response = None

    elif action.type == "initialize_filters":
        if not new_state.filters_initialized:
            new_state.selected_input_types = action.default_input_types
            new_state.filters_initialized = True

    elif action.type == "set_playground_chunk_index":
        new_state.playground_chunk_index = action.index

    elif action.type == "set_playground_article_index":
        new_state.playground_article_index = action.index

    elif action.type == "set_playground_agent_response":
        new_state.playground_agent_response = action.response

    elif action.type == "set_feedback_agent_response":
        new_state.feedback_agent_response = action.response
        new_state.feedback_agent_response_search_id = action.search_id

    return new_state


def dispatch(action: Action) -> None:
    """Dispatch an action to update the store."""
    st.session_state.store = reducer(get_store(), action)


def get_store() -> Store:
    """Get the current store from session state, creating if needed."""
    if "store" not in st.session_state:
        st.session_state.store = Store()
    return st.session_state.store


def init_store() -> None:
    """Initialize the store in session state if not present."""
    get_store()
