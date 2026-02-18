# meds2rdf/converter.py
from pathlib import Path
from rdflib import Graph
import polars as pl
import json
from pyshacl import validate

from .mapping.event_mapper import map_data_table
from .mapping.code_mapper import map_code_table
from .mapping.label_mapper import map_label_table
from .mapping.split_mapper import map_split_table
from .mapping.metadata_mapper import map_dataset_metadata

from .namespace import MEDS
from .utils.rdf_utils import run_shacl_validation
from .utils.load_utils import on_parquet

class MedsRDFConverter:
    """
    High-level object that converts an entire MEDS directory into an RDF graph.
    """

    def __init__(self, meds_root: str | Path):
        self.meds_root = Path(meds_root)
        self.graph = Graph()
        self.graph.bind("meds", MEDS)

    # ------------------------------
    # Top-level conversion API
    # ------------------------------
    def convert(
        self,
        include_dataset_metadata=True,
        include_codes=True,
        include_labels=False,
        include_splits=False,
        shacl_path: str | Path | None=None
    ):
        """
        Convert an entire MEDS dataset directory to RDF.

        Returns
        -------
        rdflib.Graph
        """

        dataset_uri = None

        # 1. Dataset metadata
        if include_dataset_metadata:
            meta_path = self.meds_root / "metadata/dataset.json"
            if meta_path.exists():
                with open(meta_path) as f:
                    meta = json.load(f)
                dataset_uri = map_dataset_metadata(self.graph, meta)

        # 2. Data tables
        on_parquet(
            files_path=list((self.meds_root / "data").rglob("*.parquet")), 
            run=lambda x: map_data_table(self.graph, x, dataset_uri)
        )

        # 3. Codes
        if include_codes:
            code_file = self.meds_root / "metadata/codes.parquet"
            if code_file.exists():
                on_parquet(
                    files_path=[code_file], 
                    run=lambda x: map_code_table(self.graph, x, dataset_uri)
                )

        # 4. Subject splits
        if include_splits:
            split_file = self.meds_root / "metadata/subject_splits.parquet"
            if split_file.exists():
                on_parquet(
                    files_path=[split_file], 
                    run=lambda x: map_split_table(self.graph, x)
                )

        # 5. Labels
        if include_labels:
            labels_root: Path = (self.meds_root / "labels")
 
            for task_dir in labels_root.iterdir():
                if not task_dir.is_dir():
                    continue
                parquet_files = list(task_dir.rglob("*.parquet"))
                if not parquet_files:
                    continue

                on_parquet(
                    files_path=parquet_files,
                    run=lambda x: map_label_table(self.graph, x)
                )

        if shacl_path is not None: 
            run_shacl_validation(self.graph, shacl_path)

        return self.graph

    # ------------------------------
    # Serialization helpers
    # ------------------------------
    def to_turtle(self, path: str | Path):
        self.graph.serialize(destination=str(path), format="turtle")

    def to_xml(self, path: str | Path):
        self.graph.serialize(destination=str(path), format="xml")

    def to_nt(self, path: str | Path):
        self.graph.serialize(destination=str(path), format="nt")
