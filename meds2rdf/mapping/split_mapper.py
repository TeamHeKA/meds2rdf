from collections.abc import Generator

import polars as pl
from rdflib import PROV, RDF, Literal, URIRef

from ..namespace import MEDS, MEDS_INSTANCES

# Map split names to RDF predicates
_split_dict = {"train": MEDS.trainSplit, "tuning": MEDS.tuningSplit, "held_out": MEDS.heldOutSplit}


def map_split_df(
    df: pl.DataFrame,
    offset: int,
    dataset_uri: URIRef | None = None,
) -> Generator[
    tuple[URIRef, URIRef, URIRef | Literal],
    None,
    None,
]:
    """
    Yield RDF triples for:
    1. Global SubjectSplit definitions (train/tuning/held_out)
    2. Subject assignments to splits from the DataFrame

    This is fully streaming and suitable for large datasets.
    """

    # ---- Emit global split definitions once ----
    for split_name, split_uri in _split_dict.items():
        yield (split_uri, RDF.type, MEDS.SubjectSplit)
        yield (split_uri, MEDS.splitName, Literal(split_name))

    # ---- Precompute column indices ----
    col_idx = {name: i for i, name in enumerate(df.columns)}

    # ---- Stream DataFrame rows ----
    for _, row in enumerate(df.iter_rows()):
        subject_id = row[col_idx["subject_id"]]
        assigned_split = row[col_idx["split"]]

        if (split_uri := _split_dict.get(assigned_split)) is None:
            raise ValueError(f"The given split name '{assigned_split}' is not valid")

        subject_uri = URIRef(MEDS_INSTANCES[f"subject/{subject_id}"])

        # ---- Assign split to subject ----
        yield (subject_uri, MEDS.assignedSplit, split_uri)

        # ---- Optional provenance ----
        if dataset_uri is not None:
            yield (subject_uri, PROV.wasDerivedFrom, dataset_uri)
