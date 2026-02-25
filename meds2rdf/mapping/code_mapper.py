from collections.abc import Generator

import polars as pl
from rdflib import Literal, URIRef
from rdflib.namespace import PROV, XSD

from ..namespace import MEDS
from ..utils.rdf_utils import generate_code, generate_code_uri, sanitize_text


def _map_parent_codes(value, code_cache, internal_code_uri):
    parent_codes = value if isinstance(value, list | tuple) else [value]

    for parent_code in parent_codes:
        if parent_code:
            # Cache external codes too
            if parent_code not in code_cache:
                code_cache[parent_code] = generate_code(
                    code_str=parent_code,
                    external=True,
                )

            parent_uri, parent_triples = code_cache[parent_code]

            yield from parent_triples

            yield (
                internal_code_uri,
                MEDS.parentCode,
                parent_uri,
            )


def map_code_df(
    df: pl.DataFrame,
    offset: int,
    dataset_uri: URIRef | None = None,
) -> Generator[
    tuple[URIRef, URIRef, URIRef | Literal],
    None,
    None,
]:
    """
    Yield triples for a batch of MEDS CodeSchema rows.
    Optimized for large DataFrames (500k+ rows).
    Avoids list materialization and repeated code generation.
    """

    # ---- Precompute column indices (O(n_cols)) ----
    col_idx = {name: i for i, name in enumerate(df.columns)}
    has_description = "description" in col_idx
    has_parent = "parent_codes" in col_idx

    # ---- Cache for generated codes (critical for scale) ----
    code_cache: dict[str, tuple[URIRef, list]] = {}

    # ---- Row streaming iteration ----
    for _, row in enumerate(df.iter_rows()):
        code_uri = generate_code_uri(code_str=row[col_idx["code"]])

        # ---- Optional description ----
        if has_description:
            desc = row[col_idx["description"]]
            if desc is not None:
                yield (
                    code_uri,
                    MEDS.codeDescription,
                    Literal(sanitize_text(str(desc)), datatype=XSD.string),
                )

        # ---- Optional parent codes ----
        if has_parent:
            parent_val = row[col_idx["parent_codes"]]
            if parent_val:
                yield from _map_parent_codes(parent_val, code_cache, internal_code_uri=code_uri)

        # ---- Provenance ----
        if dataset_uri is not None:
            yield (
                code_uri,
                PROV.wasDerivedFrom,
                dataset_uri,
            )
