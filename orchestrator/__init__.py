"""OmegaLoop Orchestrator — distributed, crash-resilient research loops. Live. Die. Repeat."""
from orchestrator.engine import (
    Orchestrator, ResearchLoop, SessionManager, GitOps, Manifest,
    MACHINE_ID, get_machine_id, make_agent_factory,
)

__all__ = [
    "Orchestrator", "ResearchLoop", "SessionManager", "GitOps", "Manifest",
    "MACHINE_ID", "get_machine_id", "make_agent_factory",
]
