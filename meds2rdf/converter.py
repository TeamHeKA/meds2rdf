# meds2rdf/converter.py
from __future__ import annotations
from pathlib import Path
from typing import Optional
import logging

from rdflib import Graph, plugin
from rdflib.store import Store
from rdflib.plugin import PluginException

from .mapping.event_mapper import map_event, map_event_df
from .mapping.code_mapper import map_code
from .mapping.label_mapper import map_label
from .mapping.split_mapper import map_split
from .mapping.metadata_mapper import map_dataset_metadata

from .namespace import MEDS, MEDS_INSTANCES
from .utils.rdf_utils import run_shacl_validation
from .utils.load_utils import load_and_parse_meds_table, load_and_parse_meds_table2, load_json, load_task_labels_files, raise_if_not_exist

logger = logging.getLogger(__name__)


class MedsRDFConverter:
    """
    Convert a MEDS dataset directory to rdflib.Graph, with optional persistent SQLAlchemy-backed store.

    Parameters
    ----------
    meds_root : str | Path
        Root folder of the MEDS dataset
    persistent_store : bool
        If True, attempt to use a persistent SQLAlchemy-backed store (requires `rdflib-sqlalchemy`).
        If False (default), uses an in-memory Graph.
    """

    def __init__(
        self,
        meds_root: str | Path,
        persistent_store: bool = False,
    ):
        self.meds_root = Path(meds_root)
        self.persistent_store = bool(persistent_store)
        self._user_store_path = Path("meds_store.sqlite")

        self.graph: Optional[Graph] = None
        self._store_cls = None
        self._initialized = False

    # ------------------------------
    # Store initialization / lifecycle
    # ------------------------------
    def _ensure_store_class(self):
        """Try to get the SQLAlchemy store plugin class, or raise a helpful error."""
        if self._store_cls is not None:
            return self._store_cls

        try:
            self._store_cls = plugin.get("SQLAlchemy", Store)
            return self._store_cls
        except PluginException:
            # Provide a helpful message for users who forgot to install rdflib-sqlalchemy
            raise RuntimeError(
                "Persistent SQL store requested but no 'SQLAlchemy' rdflib store plugin is registered. "
                "Install the plugin with `pip install rdflib-sqlalchemy` and ensure it is importable."
            ) from None

    def open_store(self):
        if self.persistent_store:
            store_cls = self._ensure_store_class()
            store = store_cls("meds_store")
            self.graph = Graph(store=store)

            if self._user_store_path is None:
                raise ValueError("persistent_store=True requires store_path or store_url")
            p = Path(self._user_store_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            db_url = f"sqlite:///{str(p)}"

            # Open the store. create=True ensures file/tables are set up.
            self.graph.open(db_url, create=True)
            logger.debug("Opened SQLAlchemy-backed graph at %s", db_url)

        else:
            # in-memory graph
            self.graph = Graph()
            logger.debug("Created in-memory graph")

        # Bind useful namespaces
        self.graph.bind("meds", MEDS)
        self.graph.bind("meds-data", MEDS_INSTANCES)

        self._initialized = True

    def close(self):
        """Close the graph/store if open. Safe to call multiple times."""
        if self.graph is None:
            return
        try:
            self.graph.close()
            logger.debug("Closed graph/store")
        finally:
            self.graph = None
            self._initialized = False

    def erase_database(self):
        """Close and remove the underlying SQLite file (if using file-based SQLite)."""
        if self.graph is not None:
            self.close()
        if self._user_store_path:
            p = Path(self._user_store_path)
            try:
                if p.exists():
                    p.unlink()
                    logger.info("Removed database file %s", p)
            except Exception as exc:
                logger.warning("Failed to remove database file %s: %s", p, exc)

    # Context manager support
    def __enter__(self) -> "MedsRDFConverter":
        # open lazily so __init__ remains cheap
        self.open_store()
        return self

    def __exit__(self, exc_type, exc, tb):
        # Always close resources on exit
        self.close()

    # ------------------------------
    # Top-level conversion API
    # ------------------------------
    def convert(
        self,
        include_dataset_metadata: bool = True,
        include_codes: bool = True,
        include_labels: bool = False,
        include_splits: bool = False,
        shacl_path: Optional[str | Path] = None,
    ) -> Graph:
        """
        Convert an entire MEDS dataset directory to RDF and return the rdflib.Graph.

        Note: This method does not automatically close the graph even if persistent_store=True.
        Use `keep_open=False` or call `.close()` when finished, or use the context manager.

        Returns
        -------
        rdflib.Graph
        """
        self.open_store()

        dataset_uri = None

        # 1. Dataset metadata
        if include_dataset_metadata:
            meta_path = self.meds_root / "metadata" / "dataset.json"
            raise_if_not_exist(meta_path)
            dataset_uri = map_dataset_metadata(self.graph, load_json(meta_path))

        # 2. Data tables
        load_and_parse_meds_table2(
             files_path=list((self.meds_root / "data").rglob("*.parquet")),
             entity="Event",
             map_df=map_event_df,
             storage=self.graph,
             provenance=dataset_uri
        )

        # 3. Codes
        if include_codes:
            load_and_parse_meds_table(
                files_path=[self.meds_root / "metadata" / "codes.parquet"],
                entity="Code",
                map=map_code,
                storage=self.graph,
                provenance=dataset_uri
            )

        # 4. Subject splits
        if include_splits:
            load_and_parse_meds_table(
                files_path=[self.meds_root / "metadata" / "subject_splits.parquet"],
                entity="SubjectSplit",
                map=map_split,
                storage=self.graph
            )

        # 5. Labels
        if include_labels:
            load_and_parse_meds_table(
                files_path=load_task_labels_files(self.meds_root / "labels"),
                entity="Label",
                map=map_label,
                storage=self.graph
            )

        # SHACL validation if requested
        if shacl_path is not None:
            run_shacl_validation(self.graph, shacl_path)

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