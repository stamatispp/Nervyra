from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any, List

ToolContext = Dict[str, Any]
ToolEntrypoint = Callable[[ToolContext], None]

@dataclass(frozen=True)
class Tool:
    id: str
    name: str
    description: str = ""
    icon: str = ""  # Qt resource path or filesystem path
    entrypoint: ToolEntrypoint | None = None
    category: str = "General"
    allowed_departments: Optional[List[str]] = None
    admin_only: bool = False
