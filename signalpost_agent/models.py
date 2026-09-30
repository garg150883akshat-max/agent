from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

VALID_STATES = {"available", "not_available", "blocked", "not_applicable", "ambiguous", "failed"}

@dataclass
class Evidence:
    source_url: str
    source_type: str
    retrieved_at: str
    published_at: str | None = None
    reporting_period: str | None = None
    quote: str | None = None
    content_hash: str | None = None
    match_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

@dataclass
class Fact:
    key: str
    value: Any
    evidence: list[Evidence] = field(default_factory=list)
    confidence: float = 1.0
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {"key": self.key, "value": self.value, "confidence": round(self.confidence, 3),
             "evidence": [e.to_dict() for e in self.evidence]}
        if self.notes:
            d["notes"] = self.notes
        return d

@dataclass
class Change:
    key: str
    old_value: Any
    new_value: Any
    evidence: list[Evidence]
    detected_at: str

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "old_value": self.old_value, "new_value": self.new_value,
                "evidence": [e.to_dict() for e in self.evidence], "detected_at": self.detected_at}

@dataclass
class CompanyResult:
    company_number: str
    status: str
    profile: dict[str, Any]
    facts: list[Fact]
    changes: list[Change]
    summary: str
    missing: list[str]
    errors: list[str]
    retrieved_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_number": self.company_number,
            "status": self.status,
            "profile": self.profile,
            "facts": [f.to_dict() for f in self.facts],
            "changes": [c.to_dict() for c in self.changes],
            "summary": self.summary,
            "missing": self.missing,
            "errors": self.errors,
            "retrieved_at": self.retrieved_at,
        }
