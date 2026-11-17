from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field


class Ticket(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=3, max_length=8000)
    order_id: str | None = Field(default=None, pattern=r"^DEMO-\d{4}$")


class Draft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=6000)
    citations: list[str]


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    approve: bool
    note: str = Field(min_length=1, max_length=1000)


class AgentState(TypedDict, total=False):
    question: str
    order_id: str | None
    intent: str
    risk: str
    evidence: list[dict]
    order: dict | None
    attempts: int
    draft: dict
    validation_errors: list[str]
    approved: bool
    review_note: str
    status: Literal["drafting", "needs_review", "answered", "reviewed", "escalated"]
    answer: str
    trace: list[dict]

