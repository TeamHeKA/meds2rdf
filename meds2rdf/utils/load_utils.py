import gzip
import json
import math
from collections.abc import Iterable
from pathlib import Path

import polars as pl
from rdflib import Graph, URIRef
from tqdm import tqdm

BATCH_SIZE = 256_000
MEDS_RDF_COHORT = Path("MEDS_rdf_cohort")

# --------------------------------------------------
# Utilities
# --------------------------------------------------


def stream_to_nt(triples: Iterable, gzip_file):
    """
    Stream triples into an already-open gzip file.
    Avoids reopening gzip per batch.
    """
    write = gzip_file.write
    for s, p, o in triples:
        write(f"{s.n3()} {p.n3()} {o.n3()} .\n")


def raise_if_not_exist(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"{path.name.capitalize()} not found at: {path}.\n"
            f"You set 'include_{path.name}=True', but it does not exist."
        )


def load_json(path: Path):
    with open(path) as f:
        return json.load(f)


def _run_with_polars(
    data: pl.LazyFrame,
    map_fn,
    entity: str,
    out_dir: Path,
    storage: Graph | None = None,
    dataset_uri: URIRef | None = None,
):
    """
    Fully streaming execution.
    No pre-scan.
    Single gzip file.
    """
    # Ensure output directory exists
    out_dir.mkdir(exist_ok=True)

    offset = 0

    # Get total number of rows in a memory-efficient way
    total_rows = data.select(pl.len()).collect()[0, 0]
    num_slices = math.ceil(total_rows / BATCH_SIZE)

    with tqdm(total=num_slices, desc=f"Processing {entity}", dynamic_ncols=True) as pbar:
        for batch in data.collect(engine="streaming").iter_slices(n_rows=BATCH_SIZE):
            if batch.is_empty():
                pbar.update(1)
                continue

            # Generate triples for this batch
            triples_iter = map_fn(batch, offset, dataset_uri)

            if storage is not None:
                # Add triples to storage
                storage.addN((s, p, o, storage) for s, p, o in triples_iter)
            else:
                # Write triples to compressed NT file
                output_file = out_dir / f"{entity}_{offset}.nt.gz"
                with gzip.open(output_file, "wt", encoding="utf-8") as gzip_file:
                    stream_to_nt(triples_iter, gzip_file)

            offset += BATCH_SIZE
            pbar.update(1)


def load_and_parse_meds_table(
    files_path: list[Path],
    entity: str,
    map_fn,
    out_dir: Path,
    storage: Graph | None,
    provenance: URIRef | None = None,
):
    for f in files_path:
        raise_if_not_exist(f)

    lazy_data = pl.scan_parquet(files_path)

    _run_with_polars(
        data=lazy_data,
        map_fn=map_fn,
        entity=entity,
        out_dir=out_dir,
        storage=storage,
        dataset_uri=provenance,
    )


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


def load_and_parse_dataset_table(
    file_path: Path,
    map_fn,
    out_dir: Path,
    storage: Graph | None,
    dataset_uri: URIRef,
):
    raise_if_not_exist(file_path)

    out_dir.mkdir(exist_ok=True)

    if storage is None:
        gzip_file = gzip.open(out_dir / "dataset.nt.gz", "wt", encoding="utf-8")
    else:
        gzip_file = None

    with tqdm(total=1, desc="Processing Dataset Metadata") as pbar:
        metadata_dict = load_json(file_path)
        if storage is not None:
            storage.addN((s, p, o, storage) for s, p, o in map_fn(metadata_dict, dataset_uri))
        else:
            stream_to_nt(map_fn(metadata_dict, dataset_uri), gzip_file)
        pbar.update(1)
