from collections.abc import Generator

import polars as pl
from rdflib import Literal, URIRef
from rdflib.namespace import PROV, RDF, XSD

from ..namespace import MEDS, MEDS_INSTANCES
from ..utils.rdf_utils import generate_code, sanitize_text


def map_event_df(
    df: pl.DataFrame, offset: int, dataset_uri: URIRef | None = None
) -> Generator[tuple[URIRef, URIRef, URIRef | Literal], None, None]:
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
        yield (
            event_uri,
            MEDS.codeString,
            Literal(sanitize_text(str(code_str)), datatype=XSD.string),
        )

        # ---- Cached code generation ----
        if code_str not in code_cache:
            code_cache[code_str] = generate_code(code_str=code_str)

        code_uri, code_triples = code_cache[code_str]

        yield from code_triples

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
            if text_val is not None and text_val != "":
                yield (
                    event_uri,
                    MEDS.textValue,
                    Literal(sanitize_text(text_val), datatype=XSD.string),
                )
