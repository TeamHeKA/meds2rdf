# meds2rdf/converter.py
from __future__ import annotations

import logging
from pathlib import Path

from rdflib import Graph, URIRef

from .mapping.code_mapper import map_code_df
from .mapping.event_mapper import map_event_df
from .mapping.label_mapper import map_label_df
from .mapping.metadata_mapper import map_dataset_metadata_df
from .mapping.split_mapper import map_split_df
from .namespace import MEDS, MEDS_INSTANCES
from .utils.load_utils import (
    load_and_parse_dataset_table,
    load_and_parse_meds_table,
    load_task_labels_files,
)

logger = logging.getLogger(__name__)


class MedsRDFConverter:
    """
    Convert a MEDS dataset directory to rdflib.Graph,
    with optional persistent SQLAlchemy-backed store.

    Parameters
    ----------
    meds_root : str | Path
        Root folder of the MEDS dataset
    """

    def __init__(
        self,
        meds_root: str | Path,
    ):
        self.meds_root = Path(meds_root)
        self.graph = None

    def load_in_memory(self):
        self.graph = Graph()
        logger.debug("Created in-memory graph")
        self.graph.bind("meds", MEDS)
        self.graph.bind("meds-data", MEDS_INSTANCES)

    def erase(self):
        del self.graph

    # Context manager support
    def __enter__(self) -> MedsRDFConverter:
        self.load_in_memory()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.erase()

    # ------------------------------
    # Top-level conversion API
    # ------------------------------
    def convert(
        self,
        include_dataset_metadata: bool = False,
        include_codes: bool = False,
        include_labels: bool = False,
        include_splits: bool = False,
    ) -> Graph | None:
        """
        Convert an entire MEDS dataset directory to RDF
        """
        dataset_uri = None

        # 1. Dataset metadata
        if include_dataset_metadata:
            import uuid

            dataset_uri = URIRef(MEDS_INSTANCES[f"dataset_metadata/{uuid.uuid4()}"])

            load_and_parse_dataset_table(
                file_path=(self.meds_root / "metadata" / "dataset.json"),
                map_fn=map_dataset_metadata_df,
                storage=self.graph,
                dataset_uri=dataset_uri,
            )

        # 2. Data tables
        load_and_parse_meds_table(
            files_path=list((self.meds_root / "data").rglob("*.parquet")),
            entity="Event",
            map_fn=map_event_df,
            storage=self.graph,
            provenance=dataset_uri,
        )

        # 3. Codes
        if include_codes:
            load_and_parse_meds_table(
                files_path=[self.meds_root / "metadata" / "codes.parquet"],
                entity="Code",
                map_fn=map_code_df,
                storage=self.graph,
                provenance=dataset_uri,
            )

        # 4. Subject splits
        if include_splits:
            load_and_parse_meds_table(
                files_path=[self.meds_root / "metadata" / "subject_splits.parquet"],
                entity="SubjectSplit",
                map_fn=map_split_df,
                storage=self.graph,
            )

        # 5. Labels
        if include_labels:
            load_and_parse_meds_table(
                files_path=load_task_labels_files(self.meds_root / "labels"),
                entity="Label",
                map_fn=map_label_df,
                storage=self.graph,
            )

        return self.graph

    # ------------------------------
    # Serialization helpers
    # ------------------------------
    def to_turtle(self, path: str | Path):
        if self.graph is None:
            raise RuntimeError("Graph is not open. Call open_store() or convert() first.")
        self.graph.serialize(destination=str(path), format="turtle")

    def to_xml(self, path: str | Path):
        if self.graph is None:
            raise RuntimeError("Graph is not open. Call open_store() or convert() first.")
        self.graph.serialize(destination=str(path), format="xml")

    def to_nt(self, path: str | Path):
        if self.graph is None:
            raise RuntimeError("Graph is not open. Call open_store() or convert() first.")
        self.graph.serialize(destination=str(path), format="nt")
