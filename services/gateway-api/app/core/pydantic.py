"""Compatibility helpers for Pydantic v1 and v2."""

from pydantic import BaseModel

try:  # pragma: no cover - depends on installed Pydantic version
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - Pydantic v1
    ConfigDict = None


class StrictBaseModel(BaseModel):
    if ConfigDict is not None:
        model_config = ConfigDict(extra="forbid")
    else:
        class Config:
            extra = "forbid"


def model_to_dict(instance):
    if hasattr(instance, "model_dump"):
        return instance.model_dump()
    return instance.dict()
