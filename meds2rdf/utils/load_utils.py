from collections.abc import Generator
from pathlib import Path
from typing import Any

import polars as pl
import pyarrow.parquet as pq
from rdflib import URIRef
from tqdm import tqdm

from meds2rdf.config import SemanticMode

from ..sinks.base import TripleSink

# --------------------------------------------------
# Utilities
# --------------------------------------------------


def map_on_load(
    data: Generator[pl.LazyFrame, Any, None],
    map_fn,
    entity: str,
    sink: TripleSink,
    batch_size: int,
    provenance: URIRef | None = None,
    total_rows: None | int = None,
    mode: None | SemanticMode = None,
):
    """
    Fully streaming execution.
    Storage-agnostic.
    """

    offset = 0

    # total_rows = data.select(pl.len()).collect(engine="streaming")[0, 0]
    # num_slices = math.ceil(total_rows / batch_size)

    with tqdm(
        total=total_rows, desc=f"Processing {entity}", dynamic_ncols=True, unit="batch"
    ) as pbar:
        for f in data:
            for batch in f.collect(engine="streaming").iter_slices(n_rows=batch_size):
                if batch.is_empty():
                    continue

                sink.add_many(map_fn(batch, offset, provenance, mode))

                offset += len(batch)
            pbar.update(offset)


def raise_if_not_exist(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"{path.name.capitalize()} not found at: {path}.\n"
            f"You set 'include_{path.name}=True', but it does not exist."
        )


def count_rows(files):
    return sum(pq.ParquetFile(f).metadata.num_rows for f in files)


def load_parquets(files_path: list[Path]):
    for f in files_path:
        raise_if_not_exist(f)

        yield pl.scan_parquet(f)


def load_json(path: Path):
    raise_if_not_exist(path)

    yield pl.read_json(path).lazy()


def load_task_labels_files(root: Path):
    labels_per_tasks_files = []
    for task_dir in root.iterdir():
        if not task_dir.is_dir():
            continue
        files = list(task_dir.rglob("*.parquet"))
        if not files:
            continue
        labels_per_tasks_files.append(files)

    return labels_per_tasks_files
