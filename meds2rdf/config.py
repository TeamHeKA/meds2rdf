# meds2rdf/config.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class MEDSSchema(Enum):
    """Enumerates the top-level MEDS datasets (schema types) that can be exported.

    Use members of this enum to indicate which parts of a MEDS dataset should
    be materialized (for example, dataset metadata, codes/vocabulary, labels,
    and subject splits).
    """

    DATASET_METADATA = auto()
    CODES = auto()
    LABELS = auto()
    SPLITS = auto()

    @classmethod
    def all(cls) -> set[MEDSSchema]:
        """Return a set containing all schema members."""
        return set(cls)


@dataclass(slots=True)
class Config:
    """Configuration for the RDF export process.

    Attributes
    ----------
    schemas:
        Set of `MEDSSchema` entries that should be exported.
    batch_size:
        Number of triples / rows that mapping functions should buffer before
        flushing to the sink. This value is passed down to streaming helpers
        and to Batch sinks (the pipeline may override it for particular sinks).
    """

    schemas: set[MEDSSchema] = field(default_factory=set)
    batch_size: int = 256_000
