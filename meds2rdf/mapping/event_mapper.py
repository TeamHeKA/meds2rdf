from typing import Generator

from rdflib import URIRef, Literal
from rdflib.namespace import RDF, XSD, PROV
import polars as pl

from ..namespace import MEDS, MEDS_INSTANCES
from ..utils.rdf_utils import generate_code

_literals_dict = {
    "time": (MEDS.time, XSD.dateTime),
    "numeric_value": (MEDS.numericValue, XSD.double),
    "text_value": (MEDS.textValue, XSD.string),
}

def map_event(
    row: tuple,
    col_idx: dict[str, int],
    row_index: int,
    dataset_uri: URIRef | None = None
) -> list[tuple[URIRef, URIRef, URIRef]]:
    triples = []
    subject_id = row[col_idx["subject_id"]]

    event_uri = URIRef(MEDS_INSTANCES[f"event/{subject_id}_{row_index}"])
    triples.append((event_uri, RDF.type, MEDS.Event))

    subject_uri = URIRef(MEDS_INSTANCES[f"subject/{subject_id}"])
    triples.append((subject_uri, RDF.type, MEDS.Subject))
    triples.append((subject_uri, MEDS.subjectId, Literal(str(subject_id), datatype=XSD.string)))
    triples.append((event_uri, MEDS.hasSubject, subject_uri))

    # Code
    code_str = row[col_idx["code"]]
    triples.append((event_uri, MEDS.codeString, Literal(str(code_str), datatype=XSD.string)))

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

    return triples


def map_event_df(
    df: pl.DataFrame,
    offset: int,
    dataset_uri: URIRef | None = None
) -> Generator[
    tuple[URIRef, URIRef, URIRef | Literal],
    None,
    None
]:
    """
    Yield triples for a batch of events.
    Optimized for large DataFrames (500k+ rows).
    Avoids to_list() materialization.
    """

    # ---- Precompute column indices (O(n_cols), done once) ----
    col_idx = {name: i for i, name in enumerate(df.columns)}

    has_time = "time" in col_idx
    has_numeric = "numeric_value" in col_idx
    has_text = "text_value" in col_idx

    # ---- Caches (major performance wins at scale) ----
    seen_subjects: set = set()
    code_cache: dict = {}

    # ---- Row streaming iteration (no Python list materialization) ----
    for i, row in enumerate(df.iter_rows()):
        sid = row[col_idx["subject_id"]]
        code_str = row[col_idx["code"]]

        subject_uri = URIRef(MEDS_INSTANCES[f"subject/{sid}"])

        # ---- Deduplicate subjects per batch ----
        if sid not in seen_subjects:
            seen_subjects.add(sid)
            yield (subject_uri, RDF.type, MEDS.Subject)
            yield (subject_uri, MEDS.subjectId, Literal(str(sid), datatype=XSD.string))

        row_index = offset + i
        event_uri = URIRef(MEDS_INSTANCES[f"event/{sid}_{row_index}"])

        yield (event_uri, RDF.type, MEDS.Event)
        yield (event_uri, MEDS.hasSubject, subject_uri)

        # ---- Code literal ----
        yield (event_uri, MEDS.codeString, Literal(str(code_str), datatype=XSD.string))

        # ---- Cached code generation ----
        if code_str not in code_cache:
            code_cache[code_str] = generate_code(code_str=code_str)

        code_uri, code_triples = code_cache[code_str]

        for triple in code_triples:
            yield triple

        yield (event_uri, MEDS.hasCode, code_uri)

        # ---- Provenance ----
        if dataset_uri is not None:
            yield (event_uri, PROV.wasDerivedFrom, dataset_uri)

        # ---- Optional literals ----
        if has_time:
            time_val = row[col_idx["time"]]
            if time_val is not None:
                yield (event_uri, MEDS.time, Literal(time_val, datatype=XSD.dateTime))

        if has_numeric:
            numeric_val = row[col_idx["numeric_value"]]
            if numeric_val is not None:
                yield (event_uri, MEDS.numericValue, Literal(numeric_val, datatype=XSD.double))

        if has_text:
            text_val = row[col_idx["text_value"]]
            if text_val is not None:
                yield (event_uri, MEDS.textValue, Literal(text_val, datatype=XSD.string))