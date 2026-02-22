from pathlib import Path
from typing import Callable
import polars as pl
import json
import os 
from rdflib import URIRef, Graph

from tqdm import tqdm
import numpy as np
import math
from concurrent.futures import ProcessPoolExecutor
import gc

BATCH_SIZE = 512_000

def raise_if_not_exist(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"{path.name.capitalize()} not found at: {path}.\n"
            f"You set 'include_{path.name}=True', but it does not exist."
        )
    
def load_json(path: Path):
    with open(path) as f:
        return json.load(f)
    

# run: Callable[[Any, int, int, URIRef], list[tuple[URIRef, URIRef, URIRef]]]
def _process_chunk_nt(args) -> list[tuple[URIRef, URIRef, URIRef]]:
    """
    Process a chunk of rows and write triples directly to an .nt file
    """
    chunk, col_idx, offset, dataset_uri, worker_id, run = args
    # filepath = os.path.join(output_dir, f"triples_worker_{worker_id}.nt")

    # with open(filepath, "w", encoding="utf-8") as f:
    #     for i, row in enumerate(chunk):
    #         triples = run(row, col_idx, offset + i, dataset_uri)
    #         for s, p, o in triples:
    #             f.write(f"{s.n3()} {p.n3()} {o.n3()} .\n")
    #         del triples
    # return filepath

    triples = []
    for i, row in enumerate(chunk):
        triples.extend(run(row, col_idx, offset + i, dataset_uri))
    return triples

def _split_list(lst, n):
    k, m = divmod(len(lst), n)
    return [
        lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)]
        for i in range(n)
    ]

def _run_in_parallel(
    files_path: list[Path],
    run: Callable[[tuple, dict[str, int], int, URIRef], list[tuple[URIRef, URIRef, URIRef]]],
    entity: str,
    graph: Graph,
    dataset_uri: URIRef | None = None,
    #output_dir = "meds2rdf/tmp_nt",
) -> None:
    """
    Stream Polars DataFrame from parquet files and generate triples in parallel
    per batch, writing to .nt files. Memory-efficient.
    """
    #os.makedirs(output_dir, exist_ok=True)

    # Lazy scan parquet
    data = pl.scan_parquet(files_path)

    # Total rows for global progress bar
    total_rows = data.select(pl.len()).collect().item()
    total_batches = math.ceil(total_rows/BATCH_SIZE)

    nt_triples = []
    batch_counter = 0

    max_workers = os.cpu_count()

    if max_workers is None:
        max_workers = 1

    # Create a single executor outside the batch loop to reuse worker processes
    with ProcessPoolExecutor(max_workers=max_workers) as executor:

        pbar = tqdm(total=total_batches, desc=f"Processing {entity} rows")
        # Stream parquet in batches
        for batch in data.collect(engine="streaming").iter_slices(n_rows=BATCH_SIZE):
            batch_rows = list(batch.iter_rows())
            if not batch_rows:
                continue

            # Split batch into worker chunks
            #chunks = np.array_split(batch_rows, max_workers)
            chunks = _split_list(batch_rows, max_workers)
            row_offsets = np.cumsum([0] + [len(c) for c in chunks[:-1]])

            col_idx = {name: i for i, name in enumerate(batch.columns)}

            args = [
                (chunk, col_idx, offset, dataset_uri, batch_counter * max_workers + i, run)
                for i, (chunk, offset) in enumerate(zip(chunks, row_offsets))
            ]

            # Parallel write for this batch
            for triples in tqdm(
                executor.map(_process_chunk_nt, args),
                total=len(chunks),
                desc=f"Writing batch {batch_counter}"
            ):
                #nt_triples.append(triples)
                graph.addN(triples)

            # --- Release memory per batch ---
            pbar.update(1)
            del batch_rows, chunks
            # gc.collect()
            batch_counter += 1

    #return nt_triples

def _run_with_polars(
    files_path: list[Path],
    run_df,
    entity: str,
    graph: Graph,
    dataset_uri: URIRef | None = None,
) -> None:
    """
    Stream parquet with Polars (multithreaded),
    map batch-wise using generator,
    and insert triples with addN().
    """

    data = pl.scan_parquet(files_path)

    total_rows = data.select(pl.len()).collect().item()
    total_batches = math.ceil(total_rows / BATCH_SIZE)

    offset = 0

    with tqdm(total=total_batches, desc=f"Processing {entity}") as pbar:

        for batch in (
            data.collect(engine="streaming")
            .iter_slices(n_rows=BATCH_SIZE)
        ):
            if batch.is_empty():
                continue

            triples_iter = run_df(batch, offset, dataset_uri)

            # addN expects (s, p, o, graph)
            graph.addN((s, p, o, graph) for s, p, o in triples_iter)

            offset += len(batch)
            pbar.update(1)


def load_and_parse_meds_table2(
    files_path: list[Path],
    entity: str,
    map_df,
    storage: Graph,
    provenance: URIRef | None = None,
):
    for f in files_path:
        raise_if_not_exist(f)

    _run_with_polars(
        files_path=files_path,
        run_df=map_df,
        entity=entity,
        graph=storage,
        dataset_uri=provenance,
    )


def load_and_parse_meds_table(
    files_path: list[Path],
    entity: str,
    map: Callable[[tuple, dict[str, int], int, URIRef], list[tuple[URIRef, URIRef, URIRef]]],
    storage: Graph,
    provenance: URIRef | None = None,
):
    for f in files_path:
        raise_if_not_exist(f)

    nt_triples = _run_in_parallel(files_path, map, entity, storage, provenance)

    #for nt_file in tqdm(nt_triples, desc=f"Loading {entity} triples into graph"):
        # try:
        #     storage.parse(nt_file, format="nt")
        # finally:
        #     if os.path.exists(nt_file):
        #         os.remove(nt_file)


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