"""Pydantic compatibility helpers for shared contracts."""

from pydantic import BaseModel

try:
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover
    ConfigDict = None


if ConfigDict is not None:

    class ContractModel(BaseModel):
        """Base model that forbids unexpected fields in Pydantic v2."""

        model_config = ConfigDict(extra="forbid")

else:

    class ContractModel(BaseModel):
        """Base model that forbids unexpected fields in Pydantic v1."""

        class Config:
            extra = "forbid"
