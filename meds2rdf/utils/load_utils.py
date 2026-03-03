import math
from pathlib import Path

import polars as pl
from rdflib import URIRef
from tqdm import tqdm

from ..sinks.base import TripleSink

# --------------------------------------------------
# Utilities
# --------------------------------------------------


def map_on_load(
    data: pl.LazyFrame,
    map_fn,
    entity: str,
    sink: TripleSink,
    batch_size: int,
    provenance: URIRef | None = None,
):
    """
    Fully streaming execution.
    Storage-agnostic.
    """

    offset = 0

    total_rows = data.select(pl.len()).collect()[0, 0]
    num_slices = math.ceil(total_rows / batch_size)

    with tqdm(total=num_slices, desc=f"Processing {entity}", dynamic_ncols=True) as pbar:
        for batch in data.collect(engine="streaming").iter_slices(n_rows=batch_size):
            if batch.is_empty():
                pbar.update(1)
                continue

            sink.add_many(map_fn(batch, offset, provenance))

            offset += batch_size
            pbar.update(1)


def raise_if_not_exist(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"{path.name.capitalize()} not found at: {path}.\n"
            f"You set 'include_{path.name}=True', but it does not exist."
        )


def load_parquets(files_path: list[Path]) -> pl.LazyFrame:
    for f in files_path:
        raise_if_not_exist(f)

    return pl.scan_parquet(files_path)


def load_json(path: Path) -> pl.LazyFrame:
    raise_if_not_exist(path)
    return pl.read_json(path).lazy()


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
