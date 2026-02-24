import gzip
import json
import math
import os
from pathlib import Path

import polars as pl
from rdflib import Graph, URIRef
from tqdm import tqdm

BATCH_SIZE = 512_000
MEDS_NT_COHORT = "MEDS_nt_cohort"


def raise_if_not_exist(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"{path.name.capitalize()} not found at: {path}.\n"
            f"You set 'include_{path.name}=True', but it does not exist."
        )


def load_json(path: Path):
    with open(path) as f:
        return json.load(f)


def stream_to_nt(generator, output_path: str):
    with gzip.open(output_path, "wt", encoding="utf-8") as f:
        # with open(output_path, "w", encoding="utf-8") as f:
        for s, p, o in generator:
            f.write(f"{s.n3()} {p.n3()} {o.n3()} .\n")


def _run_with_polars(
    data: pl.LazyFrame,
    MAP,
    entity: str,
    storage: Graph | None = None,
    dataset_uri: URIRef | None = None,
) -> None:
    total_rows = data.select(pl.len()).collect().item()
    total_batches = math.ceil(total_rows / BATCH_SIZE)

    offset = 0

    if storage is None:
        os.makedirs(f"{MEDS_NT_COHORT}/{entity}s", exist_ok=True)

    with tqdm(total=total_batches, desc=f"Processing {entity}") as pbar:
        for batch in data.collect(engine="streaming").iter_slices(n_rows=BATCH_SIZE):
            if batch.is_empty():
                continue

            triples_iter = MAP(batch, offset, dataset_uri)

            if storage is not None:
                storage.addN((s, p, o, storage) for s, p, o in triples_iter)
            else:
                stream_to_nt(
                    triples_iter,
                    output_path=f"{MEDS_NT_COHORT}/{entity}s/{entity}_{offset:06d}.nt.gz",
                )

            offset += len(batch)
            pbar.update(1)


def load_and_parse_meds_table(
    files_path: list[Path],
    entity: str,
    map,
    storage: Graph | None,
    provenance: URIRef | None = None,
):
    for f in files_path:
        raise_if_not_exist(f)

    _run_with_polars(
        data=pl.scan_parquet(files_path),
        MAP=map,
        entity=entity,
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
    map,
    storage: Graph | None,
    dataset_uri: URIRef,
):
    raise_if_not_exist(file_path)

    if storage is None:
        os.makedirs(MEDS_NT_COHORT, exist_ok=True)

    with tqdm(total=1, desc="Processing Dataset Metadata") as pbar:
        metadata_dict = load_json(file_path)
        if storage is not None:
            storage.addN((s, p, o, storage) for s, p, o in map(metadata_dict, dataset_uri))
        else:
            stream_to_nt(
                generator=map(metadata_dict, dataset_uri),
                output_path=f"{MEDS_NT_COHORT}/dataset.nt.gz",
            )
        pbar.update(1)
