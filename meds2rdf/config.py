# meds2rdf/config.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class MEDSSchema(Enum):
    """Enumerates the top-level MEDS datasets (schema types) that can be exported."""

    DATASET_METADATA = auto()
    CODES = auto()
    LABELS = auto()
    SPLITS = auto()

    @classmethod
    def all(cls) -> set[MEDSSchema]:
        """Return a set containing all schema members."""
        return set(cls)


class SemanticMode(Enum):
    """Controls how events are linked to subjects."""

    BASE = auto()
    PARTIAL = auto()
    FULL = auto()


@dataclass(slots=True)
class Config:
    """Configuration for the RDF export process.

    Attributes
    ----------
    schemas:
        Set of `MEDSSchema` entries that should be exported.
    batch_size:
        Number of triples / rows that mapping functions should buffer before
        flushing to the sink.
    mode:
        Controls how event relationships are materialized.
    """

    schemas: set[MEDSSchema] = field(default_factory=set)
    batch_size: int = 256_000
    mode: SemanticMode = SemanticMode.BASE
