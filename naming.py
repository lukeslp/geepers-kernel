"""
Shared naming registry for Dreamwalker conductor/orchestrator/agent/utility hierarchy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple, Optional


class Role(str, Enum):
    CONDUCTOR = "conductor"
    ORCHESTRATOR = "orchestrator"
    AGENT = "agent"
    UTILITY = "utility"


PREFIXES: Dict[Role, str] = {
    Role.CONDUCTOR: "conductor",
    Role.ORCHESTRATOR: "orchestrator",
    Role.AGENT: "agent",
    Role.UTILITY: "utility",
}

PACKAGE_PREFIX = "dreamwalker"


@dataclass(frozen=True)
class NamingEntry:
    role: Role
    slug: str  # canonical slug (e.g., "beltalowda", "sequential")


LEGACY_MAP: Dict[str, NamingEntry] = {
    "DreamCascadeOrchestrator": NamingEntry(Role.ORCHESTRATOR, "cascade"),
    "BeltalowdaOrchestrator": NamingEntry(Role.ORCHESTRATOR, "cascade"),
    "DreamerBeltalowdaOrchestrator": NamingEntry(Role.ORCHESTRATOR, "cascade"),
    "DreamSwarmOrchestrator": NamingEntry(Role.ORCHESTRATOR, "swarm"),
    "DreamerSwarmOrchestrator": NamingEntry(Role.ORCHESTRATOR, "swarm"),
    "SequentialOrchestrator": NamingEntry(Role.ORCHESTRATOR, "sequential"),
    "ConditionalOrchestrator": NamingEntry(Role.ORCHESTRATOR, "conditional"),
    "IterativeOrchestrator": NamingEntry(Role.ORCHESTRATOR, "iterative"),
    "AccessibilityOrchestrator": NamingEntry(Role.AGENT, "accessibility"),
    "academic-pdf-renamer": NamingEntry(Role.UTILITY, "file-academic"),
    "namecrawler": NamingEntry(Role.UTILITY, "file-sha256"),
    "fileherder": NamingEntry(Role.UTILITY, "file-herder"),
    "vision-utils": NamingEntry(Role.UTILITY, "ml-vision"),
    "reference-renamer": NamingEntry(Role.UTILITY, "file-reference"),
}


def get_identifier(role: Role, slug: str, scope: str = "internal") -> str:
    """
    Return the appropriate identifier for a component.

    Args:
        role: Role enum
        slug: canonical slug (e.g., "beltalowda")
        scope: internal|package|cli|mcp
    """
    prefix = PREFIXES[role]
    if scope == "internal":
        return f"{prefix}_{slug}"
    if scope == "package":
        return f"{PACKAGE_PREFIX}-{prefix}-{slug}"
    if scope == "cli":
        return f"{prefix}-{slug}"
    if scope == "mcp":
        return f"{prefix}.{slug}"
    raise ValueError(f"Unknown scope: {scope}")


def resolve_legacy(name: str) -> Optional[NamingEntry]:
    """
    Map a legacy class/package name to the new naming entry.
    """
    return LEGACY_MAP.get(name)


__all__ = [
    "Role",
    "PREFIXES",
    "PACKAGE_PREFIX",
    "NamingEntry",
    "LEGACY_MAP",
    "get_identifier",
    "resolve_legacy",
]

