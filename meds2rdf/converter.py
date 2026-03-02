# meds2rdf/converter.py
from __future__ import annotations

import logging
from pathlib import Path

from rdflib import URIRef

from meds2rdf.config import Config, MEDSSchema

from .mapping.code_mapper import map_code_df
from .mapping.event_mapper import map_event_df
from .mapping.label_mapper import map_label_df
from .mapping.metadata_mapper import map_dataset_metadata_df
from .mapping.split_mapper import map_split_df
from .namespace import MEDS_INSTANCES
from .sinks.base import TripleSink
from .utils.load_utils import load_json, load_parquets, load_task_labels_files, map_on_load

logger = logging.getLogger(__name__)


class MedsRDFConverter:
    """Stateless converter that materializes MEDS dataset content as RDF triples.

    The converter is intentionally stateless: it reads source files from
    `meds_root`, uses mapping functions to convert rows/records into RDF triples,
    and forwards those triples to a provided `TripleSink` (which controls
    persistence).

    Example
    -------
    >>> from meds2rdf.sinks.ntriples_sink import NTriplesSink
    >>> from meds2rdf.config import Config, MEDSSchema
    >>> sink = NTriplesSink(Path("out/events.nt.gz"), batch_size=100_000, gzip_mode=True)
    >>> cfg = Config(schemas={MEDSSchema.DATASET_METADATA, MEDSSchema.LABELS}, batch_size=100_000)
    >>> conv = MedsRDFConverter("/path/to/meds")
    >>> conv.convert(sink=sink, cfg=cfg)
    """

    def __init__(self, meds_root: str | Path):
        self.meds_root = Path(meds_root)

    def convert(self, sink: TripleSink, cfg: Config) -> None:
        """Export selected MEDS artifacts to the provided sink.

        The converter consults `cfg.schemas` to decide which parts of the
        dataset to materialize. For each selected schema, it calls a mapping
        function which returns an iterator of triples; those triples are sent
        to the provided `sink`.

        Parameters
        ----------
        sink:
            A `TripleSink` implementation that will persist or stream triples.
            The caller is responsible for creating and closing the sink; the
            converter will call `sink.close()` after export completes.
        cfg:
            Export configuration. Use `cfg.schemas` to control which artifacts
            are exported and `cfg.batch_size` to control batch sizing.

        Raises
        ------
        FileNotFoundError:
            If required source files referenced by the mapping functions are missing.
        """

        dataset_uri: URIRef | None = None

        # 1. Dataset metadata
        if MEDSSchema.DATASET_METADATA in cfg.schemas:
            import uuid

            dataset_uri = URIRef(MEDS_INSTANCES[f"dataset_metadata/{uuid.uuid4()}"])

            map_on_load(
                data=load_json(self.meds_root / "metadata" / "dataset.json"),
                map_fn=map_dataset_metadata_df,
                sink=sink,
                entity="DatasetMetdata",
                batch_size=cfg.batch_size,
                provenance=dataset_uri,
            )

        # 2. Events
        map_on_load(
            data=load_parquets(list((self.meds_root / "data").rglob("*.parquet"))),
            entity="Event",
            map_fn=map_event_df,
            sink=sink,
            batch_size=cfg.batch_size,
            provenance=dataset_uri,
        )

        # 3. Codes
        if MEDSSchema.CODES in cfg.schemas:
            map_on_load(
                data=load_parquets([self.meds_root / "metadata" / "codes.parquet"]),
                entity="Code",
                map_fn=map_code_df,
                sink=sink,
                batch_size=cfg.batch_size,
                provenance=dataset_uri,
            )

        # 4. Splits
        if MEDSSchema.SPLITS in cfg.schemas:
            map_on_load(
                data=load_parquets([self.meds_root / "metadata" / "subject_splits.parquet"]),
                entity="SubjectSplit",
                map_fn=map_split_df,
                sink=sink,
                batch_size=cfg.batch_size,
            )

        # 5. Labels
        if MEDSSchema.LABELS in cfg.schemas:
            map_on_load(
                data=load_parquets(load_task_labels_files(self.meds_root / "labels")),
                entity="Label",
                map_fn=map_label_df,
                batch_size=cfg.batch_size,
                sink=sink,
            )

        sink.close()
