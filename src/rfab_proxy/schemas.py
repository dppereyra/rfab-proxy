"""Request and response models; the OpenAPI schemas are generated from these."""

from typing import Literal

from pydantic import BaseModel, Field


class Liveness(BaseModel):
    status: Literal["alive"]


class Readiness(BaseModel):
    status: Literal["ready"]


class ErrorBody(BaseModel):
    """Falcon's JSON error body."""

    title: str = Field(examples=["503 Service Unavailable"])
    description: str | None = None
