from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, XSD, PROV
import uuid
from typing import Optional, Iterable
from ..namespace import MEDS, MEDS_INSTANCES
from ..utils.rdf_utils import *

_literals_dict = {
    "time": (MEDS.time, XSD.dateTime),
    "numeric_value": (MEDS.numericValue, XSD.double),
    "text_value": (MEDS.textValue, XSD.string),
}

def map_event(
    g: Graph,
    row: dict,
    dataset_uri: Optional[URIRef] = None,
) -> URIRef:
    """
    Map a single row of a MEDS DataSchema into a Event RDF individual.

    Parameters
    ----------
    g : Graph
        RDF graph to populate
    row : dict
        Dictionary representing a single event (subject_id, time, code, numeric_value, text_value, site_id)
    dataset_uri : Optional[URIRef]
        URI of the dataset metadata to link via prov:wasDerivedFrom
    generate_code_node : bool
        Whether to create a Code individual

    Returns
    -------
    URIRef
        URI of the created Event individual
    """
    # Create unique URI for the event
    event_uri = URIRef(MEDS_INSTANCES[f"event/{uuid.uuid4()}"])
    g.add((event_uri, RDF.type, MEDS.Event))

    # ---------------------------
    # Subject
    # ---------------------------
    subject_id = try_access_mandatory_field_value(row=row, field="subject_id", entity="Event")
    subject_uri = to_subject_node(subject_id)
    g.add((event_uri, MEDS.hasSubject, subject_uri))
    g.add((subject_uri, RDF.type, MEDS.Subject))
    g.add((subject_uri, MEDS.subjectId, Literal(str(subject_id), datatype=XSD.string)))

    # ---------------------------
    # Code
    # ---------------------------
    code_str = try_access_mandatory_field_value(row=row, field="code", entity="Event")
    g.add((event_uri, MEDS.codeString, Literal(str(code_str), datatype=XSD.string)))    
    g.add((event_uri, MEDS.hasCode, add_code(code_str=code_str, graph=g)))

    # ---------------------------
    # Link to dataset metadata if provided
    # ---------------------------
    if dataset_uri:
        g.add((event_uri, PROV.wasDerivedFrom, dataset_uri))

    for column_name, (p, dtype) in _literals_dict.items():
        if_column_is_present(column_name, row, lambda v: g.add((event_uri, p, to_literal(v, dtype))))

    return event_uri


def map_data_table(
    g: Graph,
    data: Iterable[dict],
    dataset_uri: Optional[URIRef] = None,
) -> list[URIRef]:
    """
    Map an iterable of MEDS DataSchema rows to RDF Event individuals.

    Parameters
    ----------
    g : Graph
        RDF graph to populate
    data : Iterable[dict]
        List of rows/dicts representing the MEDS DataSchema
    dataset_uri : Optional[URIRef]
        URI of the dataset metadata to link all events to
    generate_code_node : bool
        Whether to create a Code individual

    Returns
    -------
    list[URIRef]
        List of URIs of the created Event individuals
    """
    uris = []
    for row in data:
        event_uri = map_event(g, row, dataset_uri)
        uris.append(event_uri)
    return uris
