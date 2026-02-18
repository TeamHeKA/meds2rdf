from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, XSD, PROV
import uuid
from typing import Optional

from meds2rdf.utils.load_utils import BATCH_SIZE
from ..namespace import MEDS, MEDS_INSTANCES
from ..utils.rdf_utils import *
import polars as pl

_literals_dict = {
    "time": (MEDS.time, XSD.dateTime),
    "numeric_value": (MEDS.numericValue, XSD.double),
    "text_value": (MEDS.textValue, XSD.string),
}

# Keep track of subjects to avoid duplicate nodes
seen_subjects = set()

def map_event(
    row: tuple,
    col_idx: dict[str, int],
    row_index: int,
    dataset_uri: URIRef | None = None
) -> tuple[URIRef, list[tuple]]:
    """
    Map a single Polars row (tuple) to RDF triples.

    Returns a list of triples, does NOT write to the graph.
    """
    triples = []

    # Deterministic Event URI
    subject_id = row[col_idx["subject_id"]]
    event_uri = URIRef(MEDS_INSTANCES[f"event/{subject_id}/{row_index}"])
    triples.append((event_uri, RDF.type, MEDS.Event))

    # ---------------------------
    # Subject
    # ---------------------------
    subject_uri = URIRef(MEDS_INSTANCES[f"subject/{subject_id}"])
    if subject_id not in seen_subjects:
        triples.append((subject_uri, RDF.type, MEDS.Subject))
        triples.append((subject_uri, MEDS.subjectId, Literal(str(subject_id), datatype=XSD.string)))
        seen_subjects.add(subject_id)

    triples.append((event_uri, MEDS.hasSubject, subject_uri))

    # ---------------------------
    # Code
    # ---------------------------
    code_str = row[col_idx["code"]]
    triples.append((event_uri, MEDS.codeString, Literal(str(code_str), datatype=XSD.string)))
    code_uri, code_triples = generate_code(code_str=code_str)
    triples.extend(code_triples)
    triples.append((event_uri, MEDS.hasCode, code_uri))

    # ---------------------------
    # Dataset link
    # ---------------------------
    if dataset_uri:
        triples.append((event_uri, PROV.wasDerivedFrom, dataset_uri))

    # ---------------------------
    # Literals
    # ---------------------------
    for col_name, (predicate, dtype) in _literals_dict.items():
        if col_name in col_idx:
            val = row[col_idx[col_name]]
            if val is not None:
                triples.append((event_uri, predicate, Literal(val, datatype=dtype)))

    return (event_uri, triples)

def map_data_table(
    g: Graph,
    data: pl.DataFrame,
    dataset_uri: URIRef | None = None
) -> list[URIRef]:
    """
    Convert a Polars DataFrame to RDF triples, batching efficiently.
    """
    return update_graph_lazy(data, g, lambda r, ci, ri: map_event(r, ci, ri, dataset_uri))