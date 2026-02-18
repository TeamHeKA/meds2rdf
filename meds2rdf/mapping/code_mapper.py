from rdflib import Graph, URIRef
from rdflib.namespace import XSD
from typing import Optional, Iterable

from meds2rdf.utils.load_utils import BATCH_SIZE
from ..namespace import MEDS
from ..utils.rdf_utils import *
import polars as pl

def map_code(
    row: tuple,
    col_idx: dict[str, int],
    dataset_uri: URIRef | None = None
) -> tuple[URIRef, list[tuple]]:
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

    return (code_uri, triples)


def map_code_table(
    g: Graph,
    data: pl.DataFrame,
    dataset_uri: URIRef | None = None
) -> list[URIRef]:
    """
    Map an iterable of MEDS CodeSchema rows to RDF Code individuals.

    Parameters
    ----------
    g : Graph
        RDF graph to populate
    data : Iterable[dict]
        A polars lazy DataFrame representing the MEDS CodeSchema
    dataset_uri : Optional[URIRef]
        URI of the dataset metadata to link all codes to

    Returns
    -------
    list[URIRef]
        List of URIs of the created Code individuals
    """

    return update_graph_lazy(data, g, lambda r, ci, _: map_code(r, ci, dataset_uri))