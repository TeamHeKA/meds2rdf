from rdflib import RDF, Graph, Literal, URIRef
from typing import Iterable
from ..namespace import MEDS
from ..utils.rdf_utils import node_exist, try_access_mandatory_field_value, to_subject_node

_split_dict = {
    "train": MEDS.trainSplit,
    "tuning": MEDS.tuningSplit,
    "held_out": MEDS.heldOutSplit
}

def map_split(g: Graph, row: dict) -> URIRef:
    """
    Map a single row of a MEDS SubjectSplitSchema into a SubjectSplit RDF individual.

    Parameters
    ----------
    g : Graph
        RDF graph to populate
    row : dict
        Dictionary representing a single split

    Returns
    -------
    URIRef
        URI of the created SubjectSplit individual
    """

    subject_id = try_access_mandatory_field_value(row=row, field="subject_id", entity="SubjectSplit")
    assigned_split = try_access_mandatory_field_value(row=row, field="split", entity="SubjectSplit")

    if (split_uri := _split_dict.get(assigned_split)) is None:
        raise ValueError(f"The given split name '{assigned_split}' is not valid")

    if node_exist(g, node=split_uri) is False:
        g.add((split_uri, RDF.type, MEDS.SubjectSplit))
        g.add((split_uri, MEDS.splitName, Literal(assigned_split)))
        
    g.add((to_subject_node(subject_id), MEDS.assignedSplit, split_uri))
    return split_uri

def map_split_table(g: Graph, data: Iterable[dict]) -> list[URIRef]:
    """
    Map an iterable of MEDS SubjectSplitSchema rows to RDF Code individuals.

    Parameters
    ----------
    g : Graph
        RDF graph to populate
    data : Iterable[dict]
        List of rows/dicts representing the MEDS SubjectSplitSchema
    Returns
    -------
    list[URIRef]
        List of URIs of the created SubjectSplit individuals
    """
    uris = []
    for row in data:
        split_uri = map_split(g, row)
        uris.append(split_uri)
    return uris
