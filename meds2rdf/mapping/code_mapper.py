from typing import Generator

from rdflib import URIRef, Literal
from rdflib.namespace import XSD, PROV
import polars as pl

from ..namespace import MEDS
from ..utils.rdf_utils import if_exist, to_literal, generate_code, generate_code_uri


def map_code(
    row: tuple,
    col_idx: dict[str, int],
    row_index: int,
    dataset_uri: URIRef | None = None
) -> list[tuple[URIRef, URIRef, URIRef]]:
    """
    Map a single row of a MEDS CodeSchema into a Code RDF individual.

    Parameters
    ----------
    g : Graph
        RDF graph to populate
    row : dict
        Dictionary representing a single code (code, descrption, parent_codes, etc.)
    dataset_uri : Optional[URIRef]
        URI of the dataset metadata to link via prov:wasDerivedFrom

    Returns
    -------
    URIRef
        URI of the created Code individual
    """
    triples = []

    code_str = row[col_idx["code"]]
    code_uri, _triples = generate_code(code_str=code_str, dataset_uri=dataset_uri)
    triples.extend(_triples)

    if_exist(
        value=row[col_idx["description"]], 
        run=lambda x: triples.append((code_uri, MEDS.codeDescription, to_literal(x, XSD.string)))
    )

    def process_parent_code(v: str):
        if v != None and v != "": 
            ext_code_uri, _triples = generate_code(code_str=v, external=True)
            triples.extend(_triples)
            return triples.append((code_uri, MEDS.parentCode, ext_code_uri))
        
    if_exist(row[col_idx["parent_codes"]], process_parent_code)

    return triples

def _map_parent_codes(value, code_cache, internal_code_uri):
    parent_codes = (value if isinstance(value, (list, tuple)) else [value])

    for parent_code in parent_codes:
        if parent_code:
            # Cache external codes too
            if parent_code not in code_cache:
                code_cache[parent_code] = generate_code(
                    code_str=parent_code,
                    external=True,
                )

            parent_uri, parent_triples = code_cache[parent_code]

            for triple in parent_triples:
                yield triple

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

        code_uri = generate_code_uri(code_str = row[col_idx["code"]])

        # # ---- Cached code generation ----
        # if code_str not in code_cache:
        #     code_cache[code_str] = generate_code(
        #         code_str=code_str,
        #         dataset_uri=dataset_uri,
        #     )

        # code_uri, code_triples = code_cache[code_str]

        # for triple in code_triples:
        #     yield triple

        # ---- Optional description ----
        if has_description:
            description = row[col_idx["description"]]
            if description is not None:
                yield (
                    code_uri,
                    MEDS.codeDescription,
                    Literal(str(description), datatype=XSD.string),
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