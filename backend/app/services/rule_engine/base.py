from dataclasses import dataclass
from typing import Optional


@dataclass
class RuleResult:
    passed: bool
    severity: str
    message: str
    required_action: Optional[str] = None
