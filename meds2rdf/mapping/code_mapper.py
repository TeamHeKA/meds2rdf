from rdflib import Graph, URIRef
from rdflib.namespace import XSD
from typing import Optional, Iterable
from ..namespace import MEDS
from ..utils.rdf_utils import *

def map_code(
    g: Graph,
    row: dict,
    dataset_uri: Optional[URIRef] = None
) -> URIRef:
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

    code_str = try_access_mandatory_field_value(row=row, field="code", entity="Code")
    code_uri = add_code(code_str=code_str, graph=g, dataset_uri=dataset_uri)

    if_column_is_present("description", row, lambda v: g.add((code_uri, MEDS.codeDescription, to_literal(v, XSD.string))))

    def process_parent_code(v: str):
        return g.add((code_uri, MEDS.parentCode, add_code(code_str=curie_to_uri(v), graph=g, external=True)))

    if_column_is_present("parent_codes", row, process_parent_code)

    return code_uri


def map_code_table(
    g: Graph,
    data: Iterable[dict],
    dataset_uri: Optional[URIRef] = None
) -> list[URIRef]:
    """
    Map an iterable of MEDS CodeSchema rows to RDF Code individuals.

    Parameters
    ----------
    g : Graph
        RDF graph to populate
    data : Iterable[dict]
        List of rows/dicts representing the MEDS CodeSchema
    dataset_uri : Optional[URIRef]
        URI of the dataset metadata to link all codes to

    Returns
    -------
    list[URIRef]
        List of URIs of the created Code individuals
    """
    uris = []
    for row in data:
        code_uri = map_code(g, row, dataset_uri)
        uris.append(code_uri)
    return uris
