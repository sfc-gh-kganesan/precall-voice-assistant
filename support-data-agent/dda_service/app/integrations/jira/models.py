"""
Pydantic models for JIRA API responses.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class JiraTicket(BaseModel):
    """
    Represents a JIRA ticket with relevant fields for DDA.
    """

    key: str = Field(..., description="JIRA ticket key (e.g., SNOW-12345)")
    summary: str = Field(..., description="Ticket summary")
    status: str = Field(..., description="Current ticket status")
    priority: str = Field(..., description="Ticket priority")
    assignee: Optional[str] = Field(None, description="Assignee name or email")
    reporter: Optional[str] = Field(None, description="Reporter name or email")
    created: datetime = Field(..., description="Creation timestamp")
    updated: datetime = Field(..., description="Last updated timestamp")
    url: str = Field(..., description="Full URL to ticket")

    # Custom fields from Snowflake JIRA
    account_locator: Optional[str] = Field(None, description="Account locator")
    deployment: Optional[str] = Field(None, description="Deployment name")
    area: Optional[str] = Field(None, description="JIRA area")
    error_message: Optional[str] = Field(None, description="Error message")
    component: Optional[str] = Field(None, description="Component name")


class JiraSearchResponse(BaseModel):
    """
    Response model for JIRA search requests.
    """

    count: int = Field(..., description="Number of tickets returned")
    total: Optional[int] = Field(None, description="Total matching tickets")
    tickets: List[JiraTicket] = Field(..., description="List of matching tickets")


class SimilarTicketResult(BaseModel):
    """
    Result for similar ticket search with similarity score.
    """

    ticket: JiraTicket = Field(..., description="The similar ticket")
    similarity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Similarity score (0-1)"
    )
    match_reasons: List[str] = Field(
        ..., description="List of reasons why this ticket was matched"
    )


class SimilarTicketsResponse(BaseModel):
    """
    Response model for similar ticket search.
    """

    count: int = Field(..., description="Number of similar tickets found")
    tickets: List[SimilarTicketResult] = Field(
        ..., description="List of similar tickets with scores"
    )
