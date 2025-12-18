import abc
from typing import Any, Dict

from backend.models import AgentManifest

AGENT_RUNTIME_REGISTRY = {
    "post_meeting_summary": "post_meeting_summary",
}


class Agent(abc.ABC):
    """Base class for all agents (runtime interface)."""

    def __init__(self, manifest):
        self.manifest = manifest
        self.agent_id = manifest.agent_id

    @abc.abstractmethod
    def get_manifest(self) -> AgentManifest:
        """Return agent manifest metadata."""
        return self.manifest

    @abc.abstractmethod
    def run(self, input: Dict[str, Any]) -> Dict[str, Any]:
        pass
