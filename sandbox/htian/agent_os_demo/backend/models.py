import hashlib
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgentManifest(BaseModel):
    agent_id: Optional[str] = None
    name: str = Field(default="", description="The name of the agent.")
    description: str = Field(default="", description="The description of the agent.")
    version: str = Field(default="v0.1.0", description="The version of the agent.")
    runtime: str = Field(default=None, description="The runtime of the agent.")
    entrypoint: str = Field(default="", description="The entrypoint of the agent.")
    tags: List[str] = Field(default_factory=list, description="The tags of the agent.")
    input_schema: Dict[str, Any] = Field(
        default_factory=dict, description="The input schema of the agent."
    )
    output_schema: Dict[str, Any] = Field(
        default_factory=dict, description="The output schema of the agent."
    )

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="after")
    def populate_agent_id(self):
        if self.agent_id is None:
            self.agent_id = hashlib.sha256(
                f"{self.name}-{self.version}".encode("utf-8")
            ).hexdigest()
        return self


class AddAgentRequest(BaseModel):
    name: str = Field(default="", description="The name of the agent.")
    description: str = Field(default="", description="The description of the agent.")
    version: str = Field(default="v0.1.0", description="The version of the agent.")
    runtime: str = Field(default=None, description="The runtime of the agent.")
    entrypoint: str = Field(default="", description="The entrypoint of the agent.")
    tags: List[str] = Field(default_factory=list, description="The tags of the agent.")
    input_schema: Dict[str, Any] = Field(
        default_factory=dict, description="The input schema of the agent."
    )
    output_schema: Dict[str, Any] = Field(
        default_factory=dict, description="The output schema of the agent."
    )


def build_agent_manifest_from_add_agent_request(
    request: AddAgentRequest,
) -> Optional[AgentManifest]:
    try:
        return AgentManifest(
            name=request.name,
            description=request.description,
            version=request.version,
            runtime=request.runtime,
            entrypoint=request.entrypoint,
            tags=request.tags,
            input_schema=request.input_schema,
            output_schema=request.output_schema,
        )
    except Exception as e:
        raise Exception(f"Failed to build agent manifest from add agent request: {e}")


class ListAgentsRequest(BaseModel):
    """Request model for listing agents."""

    search_text: Optional[str] = Field("", description="The text to search for agents.")
    limit: Optional[int] = Field(20, description="The maximum number of agents to return.")
    offset: Optional[int] = Field(0, description="The offset to start from.")


class ListAgentsResponse(BaseModel):
    """Response model for listing agents."""

    agents: List[AgentManifest] = Field(..., description="The list of agents.")
    total: int = Field(..., description="The total number of agents.")
    limit: int = Field(..., description="The limit of the query.")
    offset: int = Field(..., description="The offset of the query.")

    @classmethod
    def from_rows(cls, rows: list, limit: int, offset: int):
        agents = [row_to_agent_manifest(r) for r in rows]
        return cls(
            agents=agents,
            total=len(rows),
            limit=limit,
            offset=offset,
        )


def row_to_agent_manifest(row: dict) -> AgentManifest:
    return AgentManifest(
        agent_id=row["AGENT_ID"],
        name=row["NAME"],
        description=row["DESCRIPTION"],
        version=row["VERSION"],
        runtime=row["RUNTIME"],
        entrypoint=row["ENTRYPOINT"],
        tags=json.loads(row["TAGS"]),
        input_schema=json.loads(row["INPUT_SCHEMA"]),
        output_schema=json.loads(row["OUTPUT_SCHEMA"]),
    )
