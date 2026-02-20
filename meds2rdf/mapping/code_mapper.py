from rdflib import URIRef
from rdflib.namespace import XSD

from ..namespace import MEDS
from ..utils.rdf_utils import if_exist, to_literal, generate_code


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
