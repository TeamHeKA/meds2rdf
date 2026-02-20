from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, XSD, PROV
from concurrent.futures import ProcessPoolExecutor
from typing import Callable, Any
import polars as pl
import os

from meds2rdf.utils.load_utils import BATCH_SIZE
from ..namespace import MEDS, MEDS_INSTANCES
from ..utils.rdf_utils import generate_code

_literals_dict = {
    "time": (MEDS.time, XSD.dateTime),
    "numeric_value": (MEDS.numericValue, XSD.double),
    "text_value": (MEDS.textValue, XSD.string),
}

def map_event_worker(
    row: tuple,
    col_idx: dict[str, int],
    row_index: int,
    dataset_uri: URIRef | None = None
):
    triples = []
    subject_id = row[col_idx["subject_id"]]

    event_uri = URIRef(MEDS_INSTANCES[f"event/{subject_id}/{row_index}"])
    triples.append((event_uri, RDF.type, MEDS.Event))

    subject_uri = URIRef(MEDS_INSTANCES[f"subject/{subject_id}"])
    triples.append((event_uri, MEDS.hasSubject, subject_uri))

    # Code
    code_str = row[col_idx["code"]]
    triples.append((event_uri, MEDS.codeString,
                    Literal(str(code_str), datatype=XSD.string)))

    code_uri, code_triples = generate_code(code_str=code_str)
    triples.extend(code_triples)
    triples.append((event_uri, MEDS.hasCode, code_uri))

    if dataset_uri:
        triples.append((event_uri, PROV.wasDerivedFrom, dataset_uri))

    # Literals
    for col_name, (predicate, dtype) in _literals_dict.items():
        if col_name in col_idx:
            val = row[col_idx[col_name]]
            if val is not None:
                triples.append((event_uri, predicate,
                                Literal(val, datatype=dtype)))

    return event_uri, triples, subject_id


def process_chunk(args):
    chunk, col_idx, offset, dataset_uri = args

    uris = []
    triples = []
    subject_ids = set()

    for i, row in enumerate(chunk):
        event_uri, t, subject_id = map_event_worker(
            row, col_idx, offset + i, dataset_uri
        )
        uris.append(event_uri)
        triples.extend(t)
        subject_ids.add(subject_id)

    return uris, triples, subject_ids


def update_graph_parallel(
    data: pl.DataFrame,
    g: Graph,
    dataset_uri: URIRef | None = None,
    max_workers: int | None = None,
) -> list[URIRef]:

    if max_workers is None:
        max_workers = os.cpu_count()

    columns = data.columns
    col_idx = {name: i for i, name in enumerate(columns)}

    rows = list(data.iter_rows())

    # Split into chunks
    chunk_size = max(1, len(rows) // max_workers)
    chunks = [
        rows[i:i + chunk_size]
        for i in range(0, len(rows), chunk_size)
    ]

    args = [
        (chunk, col_idx, i * chunk_size, dataset_uri)
        for i, chunk in enumerate(chunks)
    ]

    all_uris = []
    all_triples = []
    all_subjects = set()

    # -------- PARALLEL MAP --------
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(process_chunk, args)

        for uris, triples, subjects in results:
            all_uris.extend(uris)
            all_triples.extend(triples)
            all_subjects.update(subjects)

    # -------- SINGLE-THREAD GRAPH WRITE --------
    # Add unique subjects once
    for subject_id in all_subjects:
        subject_uri = URIRef(MEDS_INSTANCES[f"subject/{subject_id}"])
        g.add((subject_uri, RDF.type, MEDS.Subject))
        g.add((subject_uri, MEDS.subjectId,
               Literal(str(subject_id), datatype=XSD.string)))

    # Batched triple write
    for i in range(0, len(all_triples), BATCH_SIZE):
        batch = all_triples[i:i + BATCH_SIZE]
        g.addN((s, p, o, g) for s, p, o in batch)

    return all_uris

def map_data_table(
    g: Graph,
    data: pl.DataFrame,
    dataset_uri: URIRef | None = None
) -> list[URIRef]:
    """
    Convert a Polars DataFrame to RDF triples, batching efficiently.
    """
    return update_graph_parallel(data, g, dataset_uri)