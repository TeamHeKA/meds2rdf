from rdflib import URIRef, Literal
from rdflib.namespace import RDF, XSD, PROV,
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
):
    """
    Yield triples for a batch of events.
    Generator-based (no large intermediate list).
    """

    subject_ids = df["subject_id"].to_list()
    codes = df["code"].to_list()

    times = df["time"].to_list() if "time" in df.columns else None
    numeric_vals = df["numeric_value"].to_list() if "numeric_value" in df.columns else None
    text_vals = df["text_value"].to_list() if "text_value" in df.columns else None

    # ---- Deduplicate subjects per batch (major performance win) ----
    seen_subjects = set()

    for i, sid in enumerate(subject_ids):

        subject_uri = URIRef(MEDS_INSTANCES[f"subject/{sid}"])

        if sid not in seen_subjects:
            seen_subjects.add(sid)

            yield (subject_uri, RDF.type, MEDS.Subject)
            yield (
                subject_uri,
                MEDS.subjectId,
                Literal(str(sid), datatype=XSD.string),
            )

        row_index = offset + i
        event_uri = URIRef(MEDS_INSTANCES[f"event/{sid}_{row_index}"])

        yield (event_uri, RDF.type, MEDS.Event)
        yield (event_uri, MEDS.hasSubject, subject_uri)

        # ---- Code ----
        code_str = codes[i]
        yield (
            event_uri,
            MEDS.codeString,
            Literal(str(code_str), datatype=XSD.string),
        )

        code_uri, code_triples = generate_code(code_str=code_str)

        for triple in code_triples:
            yield triple

        yield (event_uri, MEDS.hasCode, code_uri)

        # ---- Provenance ----
        if dataset_uri:
            yield (event_uri, PROV.wasDerivedFrom, dataset_uri)

        # ---- Optional literals ----
        if times and times[i] is not None:
            yield (
                event_uri,
                MEDS.time,
                Literal(times[i], datatype=XSD.dateTime),
            )

        if numeric_vals and numeric_vals[i] is not None:
            yield (
                event_uri,
                MEDS.numericValue,
                Literal(numeric_vals[i], datatype=XSD.double),
            )

        if text_vals and text_vals[i] is not None:
            yield (
                event_uri,
                MEDS.textValue,
                Literal(text_vals[i], datatype=XSD.string),
            )