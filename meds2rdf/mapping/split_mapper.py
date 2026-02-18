from rdflib import RDF, Graph, Literal, URIRef
from ..namespace import MEDS
from ..utils.rdf_utils import node_exist, try_access_mandatory_field_value, to_subject_node
import polars as pl

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

def map_split_table(g: Graph, data: pl.DataFrame) -> list[URIRef]:
    """
    Map an iterable of MEDS SubjectSplitSchema rows to RDF Code individuals.

    Parameters
    ----------
    g : Graph
        RDF graph to populate
    data : pl.DataFrame
        A polars lazy DataFrame representing the MEDS SubjectSplitSchema
    Returns
    -------
    list[URIRef]
        List of URIs of the created SubjectSplit individuals
    """

    uris = []

    columns = data.columns
    for row in data.iter_rows():
        row_dict = dict(zip(columns, row))
        split_uri = map_split(g, row_dict)
        uris.append(split_uri)
    
    return uris
