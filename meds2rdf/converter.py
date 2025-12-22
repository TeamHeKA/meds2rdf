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
        data = pl.read_parquet(str(self.meds_root / "data/**/*.parquet")).to_dicts()
        map_data_table(self.graph, data, dataset_uri)

        # 3. Codes
        if include_codes:
            code_file = self.meds_root / "metadata/codes.parquet"
            if code_file.exists():
                codes = pl.read_parquet(str(code_file)).to_dicts()
                map_code_table(self.graph, codes, dataset_uri)

        # 4. Subject splits
        if include_splits:
            split_file = self.meds_root / "metadata/subject_splits.parquet"
            if split_file.exists():
                splits = pl.read_parquet(str(split_file)).to_dicts()
                map_split_table(self.graph, splits)

        # 5. Labels
        if include_labels:
            label_files = list((self.meds_root / "labels").rglob("*.parquet"))
            labels = [row for f in label_files for row in pl.read_parquet(str(f)).to_dicts()]
            map_label_table(self.graph, labels, dataset_uri)

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
